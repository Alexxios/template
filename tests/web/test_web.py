"""Exercise the empty workspace and its nested package generators."""

import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from cookiecutter.main import cookiecutter

ROOT = Path(__file__).resolve().parents[2]
JUST = str(Path(sys.prefix) / "bin/just")


@pytest.fixture
def project(tmp_path, cookiecutter_config):
    return Path(
        cookiecutter(
            str(ROOT),
            directory="src/web",
            no_input=True,
            output_dir=str(tmp_path),
            extra_context={
                "project_name": "Web Example",
            },
        )
    )


def run_just(project, recipe, *args, env=None):
    sources = [
        str(path) for group in ("services", "libs") for path in (project / group).glob("*/src")
    ]
    return subprocess.run(
        [
            JUST,
            "--justfile",
            str(project / "justfile"),
            recipe,
            *args,
        ],
        cwd=project.parent,
        env={
            **os.environ,
            "PYTHON": shlex.quote(sys.executable),
            "SCOPE_PYTHON": shlex.quote(sys.executable),
            "PYTHONPATH": os.pathsep.join(sources),
            **(env or {}),
        },
        capture_output=True,
        text=True,
        check=False,
    )


def generate(project, kind, name, *, description=""):
    return run_just(project, f"new-{kind}", name, description)


def test_workspace_starts_empty_with_tooling_and_infrastructure(project):
    for directory in ("services", "libs", "tests"):
        assert [entry.name for entry in (project / directory).iterdir()] == [".gitkeep"]
    for filename in ("LICENSE", ".pre-commit-config.yaml", "mkdocs.yml", "justfile"):
        assert (project / filename).is_file()
    assert not (project / "Makefile").exists()
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert not metadata["tool"]["uv"]["package"]
    assert metadata["tool"]["uv"]["workspace"]["members"] == ["services/*", "libs/*"]
    assert "build-system" not in metadata
    for filename in ("check_workspace.py", "new_lib.py", "new_service.py"):
        assert not (project / "scripts" / filename).exists()
    for filename in ("docker-compose.yml", "docker-compose.dev.yml"):
        assert yaml.safe_load((project / "infra" / filename).read_text()) == {"services": {}}


def test_nested_generators_create_independent_members_from_any_directory(project):
    description = """Text with "quotes", 'quotes', $(touch injected), and `touch injected`"""
    for kind, group, name in (("service", "services", "billing_api"), ("lib", "libs", "common")):
        result = generate(project, kind, name, description=description)
        assert result.returncode == 0, result.stdout + result.stderr
        member = project / group / name
        metadata = tomllib.loads((member / "pyproject.toml").read_text())
        assert metadata["project"]["name"] == name
        assert metadata["project"]["description"] == description
        assert metadata["build-system"]["build-backend"] == "setuptools.build_meta"
        assert (member / f"src/{name}/py.typed").is_file()
        assert (member / "tests/test_smoke.py").is_file()
        assert (member / "Dockerfile").exists() == (kind == "service")
        assert (member / f"src/{name}/main.py").exists() == (kind == "service")
        assert not (member / "tests/__init__.py").exists()
    assert not (project / "injected").exists()


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
    (project / "templates/service/cookiecutter.json").write_text("invalid json")
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


def test_web_is_github_only_without_a_reports_url_setting(project):
    assert (project / ".github").is_dir()
    assert not (project / ".sourcecraft").exists()
    options = json.loads((ROOT / "src/web/cookiecutter.json").read_text())
    assert not {"ci_github", "ci_sourcecraft", "reports_url", "github_repository"} & options.keys()
    config = tomllib.loads((project / "pyproject.toml").read_text())
    assert "codegen" not in config["tool"]
    assert not (project / ".github/pages.json").exists()
    # The nested generator still contains its own context after the first render.
    for kind in ("service", "lib"):
        context = json.loads((project / f"templates/{kind}/cookiecutter.json").read_text())
        assert context["package_name"] == f"new_{kind}"
        assert "_kind" not in context
        assert "reports_url" not in context
        assert "_pages_url" not in context
    result = generate(project, "lib", "common")
    assert result.returncode == 0, result.stderr
    assert "not%20published" in (project / "libs/common/README.md").read_text()


def test_web_rejects_sourcecraft_validation_before_rendering(tmp_path, cookiecutter_config):
    project = tmp_path / "unsupported"
    result = subprocess.run(
        [sys.executable, "-m", "tests.web", "render", str(project), "--ci", "sourcecraft"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "does not support sourcecraft" in result.stderr
    assert not project.exists()


def workflow(project, name):
    return yaml.load(
        (project / f".github/workflows/{name}.yml").read_text(), Loader=yaml.BaseLoader
    )


def test_ci_uses_independent_member_jobs_and_shared_checks(project):
    default = workflow(project, "ci")
    pr = workflow(project, "pull-request")
    checks = workflow(project, "checks")
    assert set(default["on"]) == {"push", "workflow_dispatch"}
    assert "github.event.repository.default_branch" in default["jobs"]["checks"]["if"]
    assert default["jobs"]["checks"]["with"]["publish"] == "true"
    assert pr["jobs"]["checks"]["uses"] == default["jobs"]["checks"]["uses"]
    assert checks["on"]["workflow_call"]["inputs"]["publish"]["default"] == "false"
    matrix = checks["jobs"]["members"]
    assert matrix["strategy"]["fail-fast"] == "false"
    assert matrix["env"]["CHECK_SCOPE"] == "${{ matrix.path }}"
    tests = next(step for step in matrix["steps"] if step.get("run") == 'just test "$CHECK_SCOPE"')
    assert "!cancelled()" in tests["if"]
    reports = checks["jobs"]["reports"]
    assert "!cancelled()" in reports["if"]
    assert "needs.discover.result == 'success'" in reports["if"]
    deploy = default["jobs"]["deploy"]
    assert "needs.checks.outputs.pages-ready == 'true'" in deploy["if"]
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert default["concurrency"]["queue"] == "max"
    assert "deploy" not in pr["jobs"]


def test_history_and_publication_are_only_enabled_on_default_branch(project):
    steps = workflow(project, "checks")["jobs"]["reports"]["steps"]
    restore = next(step for step in steps if step.get("id") == "history")
    assert restore["with"]["path"] == ".allure-history/"
    assert restore["if"] == "${{ inputs.publish }}"
    for key in ("github.ref_name", "github.run_id", "github.run_attempt"):
        assert key in restore["with"]["key"]
    for step in steps:
        if any(x in step.get("uses", "") for x in ("cache/save", "upload-pages-artifact")):
            assert step["if"] == "${{ inputs.publish }}"
    allure = next(step for step in steps if step.get("name") == "Build each scope's Allure report")
    assert 'args+=(--history-path "$history")' in allure["run"]
    assert ".allure-history/$member.jsonl" in allure["run"]
    assert '--output "$output/allure"' in allure["run"]


def test_bootstrap_pr_waits_for_publication_and_includes_templates_and_cleanup(project):
    config = workflow(project, "bootstrap-badges")
    assert set(config["on"]) == {"workflow_run"}
    setup = config["jobs"]["setup"]
    assert "github.event.repository.default_branch" in setup["if"]
    assert "head_repository.full_name == github.repository" in setup["if"]
    steps = setup["steps"]
    assert '.conclusion == "success"' in steps[0]["run"]
    bind = next(step for step in steps if step.get("id") == "bind")
    assert 'gh api "repos/$GITHUB_REPOSITORY/pages"' in bind["run"]
    assert "rm .github/workflows/bootstrap-badges.yml scripts/bind_badges.py" in bind["run"]
    pr = steps[-1]
    assert pr["with"]["branch"] == "automation/bootstrap-badges"
    assert pr["with"]["token"] == "${{ github.token }}"
    assert config["permissions"]["contents"] == "write"
    assert config["permissions"]["pull-requests"] == "write"
    assert "BOOTSTRAP_TOKEN" not in (project / ".github/workflows/bootstrap-badges.yml").read_text()
    assert set(pr["with"]["add-paths"].splitlines()) == {
        "README.md",
        "services/*/README.md",
        "libs/*/README.md",
        "templates/service/*/README.md",
        "templates/lib/*/README.md",
        "templates/readme/header.md.jinja",
        "scripts/bind_badges.py",
        ".github/workflows/bootstrap-badges.yml",
    }
    assert "steps.bind.outcome == 'success'" in pr["if"]


def test_service_and_lib_templates_can_evolve_independently(project):
    assert not (project / "templates/member").exists()
    for kind in ("service", "lib"):
        template = project / "templates" / kind
        payload = template / "{{cookiecutter.package_name}}"
        assert (payload / "Dockerfile").exists() == (kind == "service")
        assert (payload / "src/{{cookiecutter.package_name}}/main.py").exists() == (
            kind == "service"
        )
        assert not (template / "hooks/post_gen_project.py").exists()
        (payload / "kind.txt").write_text(kind)
        result = generate(project, kind, f"my_{kind}")
        assert result.returncode == 0, result.stderr
        group = "services" if kind == "service" else "libs"
        assert (project / group / f"my_{kind}/kind.txt").read_text() == kind


def test_dependabot_covers_the_workspace_and_new_services(project):
    config = yaml.safe_load((project / ".github/dependabot.yml").read_text())
    updates = {item["package-ecosystem"]: item for item in config["updates"]}
    assert set(updates) == {"github-actions", "uv", "pre-commit", "npm", "docker"}
    assert updates["uv"]["directory"] == "/"
    assert updates["npm"]["directory"] == "/.github"
    assert "/services/*" in updates["docker"]["directories"]
    assert all(item["schedule"]["interval"] == "weekly" for item in updates.values())


def test_report_template_sources_are_not_ignored_by_git(project):
    for name in ("index.html.jinja", "member.html.jinja"):
        template = project / "templates/reports" / name
        assert template.is_file()
        source = ROOT / "src/web/{{cookiecutter.project_slug}}/templates/reports" / name
        result = subprocess.run(["git", "check-ignore", "--quiet", str(source)], cwd=ROOT)
        assert result.returncode == 1
