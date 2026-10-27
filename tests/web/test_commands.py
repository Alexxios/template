"""Exercise Makefile entry points using the repository's installed Python tools."""

import pytest

from .test_web import generate, run_make
from .test_web import project as project


@pytest.mark.parametrize("kind", ["service", "lib"])
def test_creation_requires_a_name_without_changing_the_workspace(project, kind):
    readme = (project / "README.md").read_bytes()
    result = run_make(project, f"new-{kind}")
    assert result.returncode != 0
    assert f"Usage: make new-{kind} NAME=" in result.stderr
    assert (project / "README.md").read_bytes() == readme


def test_lint_checks_code_and_formatting_and_propagates_failures(project):
    assert generate(project, "lib", "common").returncode == 0
    result = run_make(project, "lint")
    assert result.returncode == 0, result.stdout + result.stderr
    source = project / "libs/common/src/common/example.py"
    source.write_text("x=1\n")
    result = run_make(project, "lint")
    assert result.returncode != 0
    assert "would be reformatted" in result.stdout
    source.write_text("import os\n")
    result = run_make(project, "lint")
    assert result.returncode != 0
    assert "F401" in result.stdout


def test_pytest_creates_standard_reports_and_propagates_failures(project):
    assert generate(project, "lib", "common").returncode == 0
    result = run_make(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    for report in ("junit.xml", "coverage.xml", "coverage.json", "coverage/index.html"):
        assert (project / "reports" / report).stat().st_size > 0
    (project / "libs/common/tests/test_smoke.py").write_text(
        "def test_failure():\n    assert False\n"
    )
    result = run_make(project, "test")
    assert result.returncode != 0
    assert "1 failed" in result.stdout
