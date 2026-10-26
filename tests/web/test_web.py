"""Exercise the empty workspace and its nested package generators."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from cookiecutter.main import cookiecutter

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project(tmp_path, cookiecutter_config):
    return Path(
        cookiecutter(
            str(ROOT),
            directory="src/web",
            no_input=True,
            output_dir=str(tmp_path),
            extra_context={"project_name": "Web Example", "ci_sourcecraft": "yes"},
        )
    )


def generate(project, kind, name, *args):
    return subprocess.run(
        [sys.executable, str(project / f"scripts/new_{kind}.py"), name, *args],
        cwd=project.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_workspace_starts_empty_with_tooling_and_infrastructure(project):
    for directory in ("services", "libs", "tests"):
        assert [entry.name for entry in (project / directory).iterdir()] == [".gitkeep"]
    for filename in ("LICENSE", ".pre-commit-config.yaml", "mkdocs.yml", "Makefile"):
        assert (project / filename).is_file()
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert not metadata["tool"]["uv"]["package"]
    assert metadata["tool"]["uv"]["workspace"]["members"] == ["services/*", "libs/*"]
    assert "build-system" not in metadata
    for filename in ("docker-compose.yml", "docker-compose.dev.yml"):
        assert yaml.safe_load((project / "infra" / filename).read_text()) == {"services": {}}


def test_nested_generators_create_independent_members_from_any_directory(project):
    for kind, group, name in (("service", "services", "billing_api"), ("lib", "libs", "common")):
        result = generate(project, kind, name, "--description", 'Text with "quotes"')
        assert result.returncode == 0, result.stdout + result.stderr
        member = project / group / name
        metadata = tomllib.loads((member / "pyproject.toml").read_text())
        assert metadata["project"]["name"] == name
        assert metadata["project"]["description"] == 'Text with "quotes"'
        assert metadata["build-system"]["build-backend"] == "setuptools.build_meta"
        assert (member / f"src/{name}/py.typed").is_file()
        assert (member / "tests/test_smoke.py").is_file()
        assert (member / "Dockerfile").exists() == (kind == "service")
        assert (member / f"src/{name}/main.py").exists() == (kind == "service")
        assert not (member / "tests/__init__.py").exists()


@pytest.mark.parametrize("name", ["../outside", "bad-name", "Bad Name", "class", "web_example"])
def test_invalid_or_root_colliding_names_leave_workspace_empty(project, name):
    result = generate(project, "service", name)
    assert result.returncode != 0
    assert "Error:" in result.stderr
    assert [p.name for p in (project / "services").iterdir()] == [".gitkeep"]


def test_duplicate_names_cannot_overwrite_or_cross_workspace_groups(project):
    assert generate(project, "lib", "common").returncode == 0
    marker = project / "libs/common/README.md"
    marker.write_text("Keep my work\n")
    for kind in ("service", "lib"):
        result = generate(project, kind, "common")
        assert result.returncode != 0
        assert "already exists" in result.stderr
    assert marker.read_text() == "Keep my work\n"
    assert not (project / "services/common").exists()


def test_failed_member_render_cleans_up_partial_output(project):
    (project / "templates/member/cookiecutter.json").write_text("invalid json")
    result = generate(project, "service", "broken")
    assert result.returncode != 0
    assert [p.name for p in (project / "services").iterdir()] == [".gitkeep"]


def test_inner_ci_fixture_scaffolds_workspace_dependencies(project):
    subprocess.run(
        [sys.executable, "-m", "tests.web", "scaffold", str(project)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for group, name, dependency in (
        ("services", "api", "shared-utils"),
        ("services", "worker", "storage"),
        ("libs", "storage", "shared-utils"),
    ):
        metadata = tomllib.loads((project / group / name / "pyproject.toml").read_text())
        assert metadata["project"]["dependencies"] == [dependency]
        assert metadata["tool"]["uv"]["sources"][dependency] == {"workspace": True}
    assert (project / "tests/test_workspace.py").is_file()


@pytest.mark.parametrize("github,sourcecraft", [("yes", "no"), ("no", "yes"), ("no", "no")])
def test_web_ci_selection(tmp_path, cookiecutter_config, github, sourcecraft):
    generated = Path(
        cookiecutter(
            str(ROOT),
            directory="src/web",
            no_input=True,
            output_dir=str(tmp_path),
            extra_context={"ci_github": github, "ci_sourcecraft": sourcecraft},
        )
    )
    assert (generated / ".github").exists() == (github == "yes")
    assert (generated / ".sourcecraft").exists() == (sourcecraft == "yes")
    # The nested generator still contains its own context after the first render.
    context = json.loads((generated / "templates/member/cookiecutter.json").read_text())
    assert context["package_name"] == "new_package"


def test_web_separates_default_branch_pages_from_pull_request_checks(project):
    workflows = project / ".github/workflows"
    default = yaml.load((workflows / "ci.yml").read_text(), Loader=yaml.BaseLoader)
    pull_request = yaml.load((workflows / "pull-request.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(default["on"]) == {"push", "workflow_dispatch"}
    assert set(pull_request["on"]) == {"pull_request"}
    checks = default["jobs"]["checks"]
    assert "github.event.repository.default_branch" in checks["if"]
    assert "github.ref == format('refs/heads/{0}'" in checks["if"]
    steps = checks["steps"]
    pages = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-pages-artifact@")
    )
    assert pages["with"]["path"] == "site/"
    assert "steps.docs.outcome == 'success'" in pages["if"]
    docs = next(step for step in steps if step.get("id") == "docs")
    # Documentation and report upload must still run after a test failure.
    assert "!cancelled()" in docs["if"]
    assert "steps.tools.outcome == 'success'" in docs["if"]
    assert "cp -R reports/. site/reports/" in docs["run"]
    pr_steps = pull_request["jobs"]["checks"]["steps"]
    assert any(step.get("with", {}).get("name") == "check-reports" for step in pr_steps)
    assert not any("pages" in step.get("uses", "") for step in pr_steps)
