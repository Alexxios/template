"""Build member reports and Shields endpoints from native Ruff/pytest outputs.

This processes existing results only; checks are run by Make or GitHub Actions.
"""

from __future__ import annotations

import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from codegen import ROOT, members
from coverage import Coverage
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPORTS = ROOT / "reports"


def read_json(path: Path):
    if not path.is_file():
        return None
    content = path.read_text().strip()
    return json.loads(content) if content else None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def relative(filename: str) -> str:
    path = Path(filename)
    if path.is_absolute() and path.is_relative_to(ROOT):
        path = path.relative_to(ROOT)
    return path.as_posix()


def badge(label: str, message: str, color: str = "lightgrey") -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def build() -> None:
    environment = Environment(
        loader=FileSystemLoader(ROOT / "templates/reports"),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
    )
    lint = read_json(REPORTS / "ruff.json")
    formatting = read_json(REPORTS / "ruff-format.json")
    # Empty output after a tool/configuration error must not be called a passing check.
    lint_available = all(
        isinstance(findings, list)
        and (os.environ.get(outcome, "success") == "success" or bool(findings))
        for findings, outcome in ((lint, "LINT_OUTCOME"), (formatting, "FORMAT_OUTCOME"))
    )
    cases = (
        list(ET.parse(REPORTS / "junit.xml").iter("testcase"))
        if (REPORTS / "junit.xml").is_file()
        else None
    )
    test_error = cases is None or any(
        error.get("message") == "collection failure" or not case.get("file")
        for case in cases
        for error in case.findall("error")
    )
    coverage_json = read_json(REPORTS / "coverage.json")
    coverage_files = coverage_json.get("files", {}) if coverage_json else {}
    coverage = None
    if (ROOT / ".coverage").is_file():
        coverage = Coverage(data_file=str(ROOT / ".coverage"), config_file=False)
        coverage.load()
    # Remove obsolete member output when rebuilding locally after a rename/removal.
    for group in ("services", "libs"):
        shutil.rmtree(REPORTS / group, ignore_errors=True)
    rows = []
    for member in members():
        path = member.relative_to(ROOT).as_posix()
        prefix = path + "/"
        output = REPORTS / path
        output.mkdir(parents=True, exist_ok=True)
        findings = [
            item
            for item in (lint or []) + (formatting or [])
            if relative(item["filename"]).startswith(prefix)
        ]
        member_cases = [
            case
            for case in cases or []
            if relative(case.get("file", "")).startswith(prefix + "tests/")
        ]
        failed = sum(
            case.find("failure") is not None or case.find("error") is not None
            for case in member_cases
        )
        skipped = sum(case.find("skipped") is not None for case in member_cases)
        passed = len(member_cases) - failed - skipped
        files = {
            name: data
            for name, data in coverage_files.items()
            if relative(name).startswith(prefix + "src/")
        }
        total = sum(
            data["summary"]["num_statements"] + data["summary"].get("num_branches", 0)
            for data in files.values()
        )
        covered = sum(
            data["summary"]["covered_lines"] + data["summary"].get("covered_branches", 0)
            for data in files.values()
        )
        percent = 100 * covered / total if total and not test_error else None
        badges = {
            "lint": badge("lint", "unavailable"),
            "tests": badge("tests", "unavailable"),
            "coverage": badge("coverage", "no data"),
        }
        if lint_available:
            badges["lint"] = badge(
                "lint",
                f"{len(findings)} issue{'s' if len(findings) != 1 else ''}"
                if findings
                else "passing",
                "red" if findings else "brightgreen",
            )
        if not test_error:
            if failed:
                badges["tests"] = badge("tests", f"{failed} failed", "red")
            elif passed:
                badges["tests"] = badge("tests", f"{passed} passed", "brightgreen")
            else:
                badges["tests"] = badge("tests", "skipped" if skipped else "no tests")
        if percent is not None:
            color = "brightgreen" if percent >= 90 else "yellow" if percent >= 75 else "red"
            badges["coverage"] = badge("coverage", f"{percent:.1f}%", color)
        has_coverage = bool(coverage is not None and total and not test_error)
        if has_coverage:
            coverage.html_report(
                include=[str(member / "src" / "*")],
                directory=str(output / "coverage"),
                title=f"Coverage for {path}",
            )
        row = {
            "path": path,
            "name": member.name,
            "badges": badges,
            "tests": {"passed": passed, "failed": failed, "skipped": skipped},
            "coverage": {"covered": covered, "total": total, "percent": percent},
            "has_coverage": has_coverage,
        }
        write_json(output / "summary.json", row)
        write_json(output / "lint.json", findings)
        write_json(output / "coverage.json", {"files": files, "totals": row["coverage"]})
        suite = ET.Element(
            "testsuite",
            name=path,
            tests=str(len(member_cases)),
            failures=str(sum(case.find("failure") is not None for case in member_cases)),
            errors=str(sum(case.find("error") is not None for case in member_cases)),
            skipped=str(skipped),
        )
        suite.extend(member_cases)
        ET.ElementTree(suite).write(output / "junit.xml", encoding="utf-8", xml_declaration=True)
        for label, data in badges.items():
            write_json(output / "badges" / f"{label}.json", data)
        (output / "index.html").write_text(
            environment.get_template("member.html.jinja").render(member=row)
        )
        rows.append(row)
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "index.html").write_text(
        environment.get_template("index.html.jinja").render(members=rows)
    )


if __name__ == "__main__":
    build()
