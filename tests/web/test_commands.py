"""Exercise justfile entry points using the repository's installed Python tools."""

import pytest

from .test_web import generate, run_just
from .test_web import project as project


@pytest.mark.parametrize("kind", ["service", "lib"])
def test_creation_requires_a_name_without_changing_the_workspace(project, kind):
    readme = (project / "README.md").read_bytes()
    result = run_just(project, f"new-{kind}")
    assert result.returncode != 0
    assert f"just new-{kind} name [description]" in result.stderr
    assert (project / "README.md").read_bytes() == readme


def test_lint_checks_code_and_formatting_and_propagates_failures(project):
    assert generate(project, "lib", "common").returncode == 0
    result = run_just(project, "lint")
    assert result.returncode == 0, result.stdout + result.stderr
    source = project / "libs/common/src/common/example.py"
    source.write_text("x=1\n")
    result = run_just(project, "lint")
    assert result.returncode != 0
    assert "unformatted" in result.stdout or "format" in result.stdout
    source.write_text("import os\n")
    result = run_just(project, "lint")
    assert result.returncode != 0
    assert "F401" in result.stdout
    result = run_just(project, "check", "libs/common")
    assert result.returncode != 0
    assert (project / "reports/libs/common/junit.xml").is_file()


def test_pytest_creates_standard_reports_and_propagates_failures(project):
    assert generate(project, "lib", "common").returncode == 0
    result = run_just(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    for report in ("junit.xml", "coverage.xml", "coverage.json", "coverage/index.html"):
        assert (project / "reports/libs/common" / report).stat().st_size > 0
    (project / "libs/common/tests/test_smoke.py").write_text(
        "def test_failure():\n    assert False\n"
    )
    assert generate(project, "lib", "later").returncode == 0
    result = run_just(project, "test")
    assert result.returncode != 0
    assert "1 failed" in result.stdout
    assert (project / "reports/libs/later/test.exit").read_text() == "0\n"
    assert (project / "reports/integration/test.exit").read_text() == "5\n"


def test_positional_scope_only_checks_the_selected_member(project):
    for name in ("common", "broken"):
        assert generate(project, "lib", name).returncode == 0
    (project / "libs/broken/tests/test_smoke.py").write_text(
        'import os\n\nraise RuntimeError("Do not collect another member")\n'
    )
    # A directory matching the recipe name must not suppress the check.
    (project / "check").mkdir()
    result = run_just(project, "check", "libs/common")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert (project / "reports/libs/common/junit.xml").is_file()
    assert (project / "reports/libs/common/ruff.json").is_file()
    assert not (project / "reports/libs/broken").exists()
    assert not (project / "reports/integration").exists()


def test_format_scope_only_changes_selected_member(project):
    for name in ("common", "other"):
        assert generate(project, "lib", name).returncode == 0
        (project / f"libs/{name}/src/{name}/example.py").write_text("value=1\n")
    result = run_just(project, "format", "libs/common")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "libs/common/src/common/example.py").read_text() == "value = 1\n"
    assert (project / "libs/other/src/other/example.py").read_text() == "value=1\n"


@pytest.mark.parametrize("recipe", ["test", "lint", "check", "format"])
@pytest.mark.parametrize("scope", ["libs/missing", "../outside"])
def test_unknown_scope_does_not_run_checks(project, recipe, scope):
    result = run_just(project, recipe, scope)
    assert result.returncode != 0
    assert f"Unknown scope: {scope}" in result.stderr
    assert not (project / "reports").exists()
