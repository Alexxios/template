"""Render reports and badge JSON from each scope's native check outputs."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from workspace import ROOT, scopes

REPORTS = ROOT / "reports"


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except OSError, ValueError:
        return None


def exit_code(directory: Path, check: str) -> int | None:
    try:
        return int((directory / f"{check}.exit").read_text())
    except OSError, ValueError:
        return None


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def badge(label: str, message: str, color: str = "lightgrey") -> dict:
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def summarize(path: str) -> dict:
    directory = REPORTS / path
    lint = read_json(directory / "ruff.json")
    formatting = read_json(directory / "ruff-format.json")
    lint_available = all(
        isinstance(findings, list) and exit_code(directory, check) in (0, 1)
        for findings, check in ((lint, "lint"), (formatting, "format"))
    )
    try:
        cases = list(ET.parse(directory / "junit.xml").iter("testcase"))
    except OSError, ET.ParseError:
        cases = None
    tests_available = cases is not None and exit_code(directory, "test") in (0, 1, 5)
    failed = sum(
        case.find("failure") is not None or case.find("error") is not None for case in cases or []
    )
    skipped = sum(case.find("skipped") is not None for case in cases or [])
    passed = len(cases or []) - failed - skipped
    coverage = read_json(directory / "coverage.json")
    totals = coverage.get("totals", {}) if coverage else {}
    total = totals.get("num_statements", 0) + totals.get("num_branches", 0)
    covered = totals.get("covered_lines", 0) + totals.get("covered_branches", 0)
    percent = 100 * covered / total if total and tests_available else None
    badges = {
        "lint": badge("lint", "unavailable"),
        "tests": badge("tests", "unavailable"),
        "coverage": badge("coverage", "no data"),
    }
    if lint_available:
        count = len(lint) + len(formatting)
        badges["lint"] = badge(
            "lint",
            f"{count} issue{'s' if count != 1 else ''}" if count else "passing",
            "red" if count else "brightgreen",
        )
    if tests_available:
        if failed:
            badges["tests"] = badge("tests", f"{failed} failed", "red")
        elif passed:
            badges["tests"] = badge("tests", f"{passed} passed", "brightgreen")
        else:
            badges["tests"] = badge("tests", "skipped" if skipped else "no tests")
    if percent is not None:
        color = "brightgreen" if percent >= 90 else "yellow" if percent >= 75 else "red"
        badges["coverage"] = badge("coverage", f"{percent:.1f}%", color)
    if not tests_available:
        shutil.rmtree(directory / "coverage", ignore_errors=True)
    row = {
        "path": path,
        "badges": badges,
        "tests": {"passed": passed, "failed": failed, "skipped": skipped},
        "coverage": {"covered": covered, "total": total, "percent": percent},
        "has_coverage": percent is not None and (directory / "coverage/index.html").is_file(),
        "has_allure": (directory / "allure/index.html").is_file(),
        "back": "../" * len(Path(path).parts),
    }
    write_json(directory / "summary.json", row)
    for label, data in badges.items():
        write_json(directory / "badges" / f"{label}.json", data)
    return row


def build() -> None:
    environment = Environment(
        loader=FileSystemLoader(ROOT / "templates/reports"),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
    )
    paths = scopes()
    # Discard reports for removed/renamed members when rebuilding locally.
    for group in ("services", "libs"):
        for directory in (REPORTS / group).glob("*"):
            if directory.is_dir() and directory.relative_to(REPORTS).as_posix() not in paths:
                shutil.rmtree(directory)
    rows = [summarize(path) for path in paths]
    for row in rows:
        (REPORTS / row["path"] / "index.html").write_text(
            environment.get_template("member.html.jinja").render(member=row)
        )
    (REPORTS / "index.html").write_text(
        environment.get_template("index.html.jinja").render(members=rows)
    )


if __name__ == "__main__":
    build()
