"""Validate automatic registration and generated-file maintenance."""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from cookiecutter.main import cookiecutter

from scripts.new_template import create_template
from scripts.sync_templates import sync

ROOT = Path(__file__).resolve().parents[1]


def test_new_template_registers_workflow_fixture_and_status(collection, tmp_path):
    create_template("python-lib", root=collection)
    workflow = collection / ".github/workflows/validate-python-lib.yml"
    job = yaml.safe_load(workflow.read_text())["jobs"]["validate"]
    assert job["env"]["TEMPLATE_MODULE"] == "tests.python_lib"
    assert "validate-python-lib.yml/badge.svg" in (collection / "README.md").read_text()
    sourcecraft = yaml.safe_load((collection / ".sourcecraft/ci.yaml").read_text())
    assert "validate-python-lib" in sourcecraft["workflows"]
    project = tmp_path / "ci-project"
    for command in ("render", "scaffold"):
        subprocess.run(
            [sys.executable, "-m", "tests.python_lib", command, str(project)],
            cwd=collection,
            check=True,
            capture_output=True,
            text=True,
        )
    assert (project / "example.py").is_file()
    assert (project / "test_example.py").is_file()
    assert not sync(collection, check=True)


def test_sync_registers_templates_created_directly(collection):
    cookiecutter(
        str(collection / "templates/cookiecutter"),
        no_input=True,
        output_dir=str(collection / "src"),
        extra_context={"template_name": "direct"},
    )
    assert sync(collection, check=True)
    assert not (collection / "tests/direct").exists()
    sync(collection)
    assert (collection / "tests/direct/scaffold.py").is_file()
    assert (collection / ".github/workflows/validate-direct.yml").is_file()


def test_sync_preserves_fixtures_and_readme_body_and_detects_drift(collection):
    create_template("custom", root=collection)
    scaffold = collection / "tests/custom/scaffold.py"
    scaffold.write_text("# My custom fixture\n")
    config = collection / "tests/custom/validation.toml"
    config.write_text(config.read_text().replace('"ci.yml"', '"inner.yml"'))
    readme = collection / "README.md"
    readme.write_text(readme.read_text() + "\nMy documentation.\n")
    before = readme.read_text()
    workflow = collection / ".github/workflows/validate-custom.yml"
    assert workflow in sync(collection, check=True)
    assert "inner.yml" not in workflow.read_text()
    sync(collection)
    assert "inner.yml" in workflow.read_text()
    assert scaffold.read_text() == "# My custom fixture\n"
    assert readme.read_text() == before
    assert not sync(collection, check=True)


def test_package_name_collisions_rollback_new_template(collection):
    create_template("python-lib", root=collection)
    before = (collection / "README.md").read_text()
    with pytest.raises(ValueError, match="share"):
        create_template("python_lib", root=collection)
    assert not (collection / "src/python_lib").exists()
    assert (collection / "src/python-lib").is_dir()
    assert (collection / "README.md").read_text() == before


def test_existing_test_modules_cannot_be_shadowed(collection):
    with pytest.raises(FileExistsError, match="test module"):
        create_template("support", root=collection)
    assert not (collection / "src/support").exists()
    assert (collection / "tests/support.py").is_file()


def test_failed_registration_restores_files_and_can_be_retried(collection, monkeypatch):
    original = Path.write_text
    readme = (collection / "README.md").read_text()

    def fail_once(path, *args, **kwargs):
        if path == collection / ".sourcecraft/ci.yaml":
            monkeypatch.setattr(Path, "write_text", original)
            raise OSError("Write failed")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_once)
    with pytest.raises(OSError, match="Write failed"):
        create_template("custom", root=collection)
    assert not (collection / "src/custom").exists()
    assert not (collection / "tests/custom").exists()
    assert (collection / "README.md").read_text() == readme
    create_template("custom", root=collection)
    assert not sync(collection, check=True)


def test_sync_does_not_overwrite_handwritten_workflows(collection):
    workflow = collection / ".github/workflows/validate-custom.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# Hand-written workflow\n")
    with pytest.raises(FileExistsError, match="hand-written"):
        create_template("custom", root=collection)
    assert workflow.read_text() == "# Hand-written workflow\n"
    assert not (collection / "src/custom").exists()
    assert not (collection / "tests/custom").exists()


def test_sync_removes_only_obsolete_generated_workflows(collection):
    create_template("custom", root=collection)
    shutil.rmtree(collection / "src/custom")
    manual = collection / ".github/workflows/validate-handwritten.yml"
    manual.write_text("# Hand-written workflow\n")
    sync(collection)
    assert not (collection / ".github/workflows/validate-custom.yml").exists()
    assert manual.exists()
    assert (collection / "tests/custom/scaffold.py").exists()
    assert "validate-custom.yml" not in (collection / "README.md").read_text()


@pytest.mark.parametrize(
    "template, ci", [("base", "github"), ("base", "sourcecraft"), ("web", "github")]
)
def test_existing_templates_share_render_and_scaffold_cli(
    template, ci, tmp_path, cookiecutter_config
):
    project = tmp_path / "ci-project"
    for command, extra in (("render", ["--ci", ci]), ("scaffold", [])):
        subprocess.run(
            [sys.executable, "-m", f"tests.{template}", command, str(project), *extra],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    assert (project / ".github").exists() == (ci == "github")
    assert (project / ".sourcecraft").exists() == (ci == "sourcecraft")
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert metadata["project"]["requires-python"].replace(" ", "") == ">=3.14"
    if template == "base":
        assert (project / "src/pkg_gamma/py.typed").is_file()
    else:
        assert (project / "tests/test_workspace.py").is_file()


def test_repository_generated_files_are_current():
    assert not sync(ROOT, check=True)
