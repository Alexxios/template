"""Build member reports from real, deliberately different Ruff and pytest results."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from .test_web import generate, run_just
from .test_web import project as project


def build_reports(project, *, lint=True):
    if lint:
        run_just(project, "lint")
    result = subprocess.run(
        [sys.executable, str(project / "scripts/build_reports.py")],
        cwd=project.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def member_report(project, path):
    return json.loads((project / "reports" / path / "summary.json").read_text())


def test_member_badges_and_click_targets_use_only_that_members_results(project):
    for kind, name in (("service", "api"), ("lib", "common"), ("lib", "common_extra")):
        assert generate(project, kind, name).returncode == 0
    (project / "libs/common/src/common/branch.py").write_text(
        "def choose(value):\n    if value:\n        return 1\n    return 0\n"
    )
    (project / "libs/common/tests/test_failure.py").write_text(
        "import os\n\n\ndef test_failure():\n    raise AssertionError\n"
    )
    (project / "libs/common_extra/src/common_extra/unformatted.py").write_text("value=1\n")
    (project / "tests/test_integration.py").write_text(
        "from common.branch import choose\n\n\ndef test_choose():\n    assert choose(True) == 1\n"
    )
    result = run_just(project, "test")
    assert result.returncode != 0
    assert "1 failed, 1 passed" in result.stdout
    assert result.stdout.count("1 passed") == 4
    build_reports(project)
    common = member_report(project, "libs/common")
    extra = member_report(project, "libs/common_extra")
    api = member_report(project, "services/api")
    assert common["tests"] == {"passed": 1, "failed": 1, "skipped": 0}
    assert common["badges"]["tests"]["message"] == "1 failed"
    assert common["badges"]["coverage"]["message"] == "14.3%"
    assert extra["badges"]["tests"]["message"] == api["badges"]["tests"]["message"] == "1 passed"
    assert extra["badges"]["coverage"]["message"] == "50.0%"
    assert common["badges"]["lint"]["message"] == extra["badges"]["lint"]["message"] == "1 issue"
    assert api["badges"]["lint"]["message"] == "passing"
    for path in ("libs/common", "libs/common_extra", "services/api"):
        report = project / "reports" / path
        for item in json.loads((report / "ruff.json").read_text()):
            assert f"/{path}/" in item["filename"]
        for filename in json.loads((report / "coverage.json").read_text())["files"]:
            assert filename.startswith("src/")
        for case in ET.parse(report / "junit.xml").iter("testcase"):
            assert case.get("classname").startswith("tests.")
        assert (report / "index.html").is_file()
        assert (report / "coverage/index.html").is_file()
        for label in ("lint", "tests", "coverage"):
            assert json.loads((report / f"badges/{label}.json").read_text())["schemaVersion"] == 1
    assert "common_extra" not in (project / "reports/libs/common/coverage/index.html").read_text()
    assert list((project / "reports/libs/common/allure-results").glob("*-result.json"))


@pytest.mark.parametrize(
    "content, message",
    [
        ("", "no tests"),
        (
            'import pytest\n\n\n@pytest.mark.skip(reason="example")\ndef test_skipped():\n    pass\n',
            "skipped",
        ),
        ('raise RuntimeError("collection error")\n', "unavailable"),
    ],
)
def test_missing_skipped_or_interrupted_tests_do_not_reuse_a_passing_badge(
    project, content, message
):
    assert generate(project, "lib", "common").returncode == 0
    assert run_just(project, "test").returncode == 0
    build_reports(project)
    assert member_report(project, "libs/common")["badges"]["tests"]["message"] == "1 passed"
    (project / "libs/common/tests/test_smoke.py").write_text(content)
    run_just(project, "test")
    build_reports(project)
    result = member_report(project, "libs/common")
    assert result["badges"]["tests"]["message"] == message
    if message == "unavailable":
        assert result["badges"]["coverage"]["message"] == "no data"
        assert not (project / "reports/libs/common/coverage").exists()


def test_missing_reports_and_broken_lint_configuration_never_report_success(project):
    assert generate(project, "lib", "common").returncode == 0
    manifest = project / "pyproject.toml"
    manifest.write_text(manifest.read_text() + "\n[tool.ruff.invalid]\nvalue = true\n")
    build_reports(project)
    result = member_report(project, "libs/common")
    assert result["badges"]["lint"]["message"] == "unavailable"
    assert result["badges"]["tests"]["message"] == "unavailable"
    assert result["badges"]["coverage"]["message"] == "no data"


def test_collection_failure_is_confined_to_one_member(project):
    assert generate(project, "lib", "broken").returncode == 0
    assert generate(project, "service", "healthy").returncode == 0
    (project / "libs/broken/tests/test_smoke.py").write_text(
        'raise RuntimeError("collection failed")\n'
    )
    result = run_just(project, "test")
    assert result.returncode != 0
    build_reports(project)
    assert member_report(project, "libs/broken")["badges"]["tests"]["message"] == "unavailable"
    assert member_report(project, "services/healthy")["badges"]["tests"]["message"] == "1 passed"
    native_coverage = json.loads((project / "reports/services/healthy/coverage.json").read_text())
    expected_coverage = f"{native_coverage['totals']['percent_covered']:.1f}%"
    assert (
        member_report(project, "services/healthy")["badges"]["coverage"]["message"]
        == expected_coverage
    )


def test_tool_startup_failure_cannot_reuse_old_lint_results(project):
    assert generate(project, "lib", "common").returncode == 0
    build_reports(project)
    assert member_report(project, "libs/common")["badges"]["lint"]["message"] == "passing"
    result = run_just(project, "lint", "libs/common", env={"PYTHON": "false"})
    assert result.returncode != 0
    build_reports(project, lint=False)
    assert member_report(project, "libs/common")["badges"]["lint"]["message"] == "unavailable"
