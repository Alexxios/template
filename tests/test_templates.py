"""Test template creation and generation through Cookiecutter's directory selector."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from cookiecutter.main import cookiecutter

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("new_template", ROOT / "scripts/new_template.py")
new_template = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(new_template)
TEMPLATES = sorted(path.parent.name for path in (ROOT / "src").glob("*/cookiecutter.json"))


@pytest.fixture
def collection(tmp_path, cookiecutter_config):
    root = tmp_path / "collection"
    shutil.copytree(ROOT / "templates/cookiecutter", root / "templates/cookiecutter")
    (root / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts/new_template.py", root / "scripts/new_template.py")
    return root


@pytest.fixture
def cookiecutter_config(tmp_path, monkeypatch):
    config = tmp_path / "cookiecutter-config.json"
    config.write_text(
        json.dumps(
            {
                "cookiecutters_dir": str(tmp_path / "cookiecutters"),
                "replay_dir": str(tmp_path / "replay"),
            }
        )
    )
    monkeypatch.setenv("COOKIECUTTER_CONFIG", str(config))
    return config


def render(root, name, tmp_path, cookiecutter_config, **context):
    return Path(
        cookiecutter(
            str(root),
            directory=f"src/{name}",
            no_input=True,
            config_file=str(cookiecutter_config),
            output_dir=str(tmp_path / "generated"),
            extra_context={
                "project_name": "Generated Example",
                "python_version": "3.14",
                "python_min_version": "3.14",
                "init_git": "no",
                **context,
            },
        )
    )


@pytest.mark.parametrize("name", TEMPLATES)
def test_collection_template_renders(name, tmp_path, cookiecutter_config):
    project = render(ROOT, name, tmp_path, cookiecutter_config)
    assert project.is_dir()
    assert (project / "README.md").is_file()
    tomllib.loads((project / "pyproject.toml").read_text())


def test_base_preserves_tooling_and_nested_package_helper(tmp_path, cookiecutter_config):
    project = render(ROOT, "base", tmp_path, cookiecutter_config)
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "generated_example"
    assert metadata["build-system"]["build-backend"] == "setuptools.build_meta"
    assert "py314" in (project / "tox.ini").read_text()
    assert "__PY_FACTORS__" not in (project / "tox.ini").read_text()
    for filename in (".pre-commit-config.yaml", "LICENSE", "mkdocs.yml", "docs/usage.md"):
        assert (project / filename).is_file()
    result = subprocess.run(
        [
            sys.executable,
            str(project / "scripts/new_package.py"),
            "--no-input",
            "package_name=extra",
        ],
        cwd=tmp_path,
        env={**os.environ, "COOKIECUTTER_CONFIG": str(cookiecutter_config)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "src/extra/py.typed").is_file()
    assert (project / "tests/extra/test_smoke.py").is_file()
    assert not (project / "tests/extra/__init__.py").exists()


def test_new_template_contains_only_tooling(collection, tmp_path, cookiecutter_config):
    destination = new_template.create_template("python-lib", root=collection)
    payload = destination / "{{cookiecutter.project_slug}}"
    assert "{{cookiecutter.project_slug}}" in (payload / "pyproject.toml").read_text()
    # Generated templates do not depend on the seed or on src/base.
    shutil.rmtree(collection / "templates")
    project = render(collection, "python-lib", tmp_path, cookiecutter_config)
    for filename in (
        "Makefile",
        "LICENSE",
        "pyproject.toml",
        "README.md",
        ".gitignore",
        "mkdocs.yml",
    ):
        assert (project / filename).is_file()
    for directory in ("src", "tests", "services", "libs", "scripts", "templates"):
        assert not (project / directory).exists()
    metadata = tomllib.loads((project / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "generated-example"
    assert metadata["project"]["dependencies"] == []
    assert not metadata["tool"]["uv"]["package"]
    assert "build-system" not in metadata
    assert "testpaths" not in metadata["tool"]["pytest"]["ini_options"]
    assert "src" not in metadata["tool"]["ruff"]
    assert metadata["tool"]["coverage"]["run"]["source"] == ["."]
    assert (project / ".github/workflows/ci.yml").is_file()
    assert not (project / ".sourcecraft").exists()


def test_cli_uses_cookiecutter_seed_from_any_directory(collection, tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(collection / "scripts/new_template.py"),
            "cli-tool",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--directory src/cli-tool" in result.stdout
    assert (collection / "src/cli-tool/{{cookiecutter.project_slug}}/Makefile").is_file()


def test_seed_can_be_used_directly_with_cookiecutter(tmp_path, cookiecutter_config):
    template = Path(
        cookiecutter(
            str(ROOT / "templates/cookiecutter"),
            no_input=True,
            config_file=str(cookiecutter_config),
            output_dir=str(tmp_path / "src"),
            extra_context={"template_name": "direct"},
        )
    )
    project = render(tmp_path, template.name, tmp_path, cookiecutter_config)
    assert (project / "Makefile").is_file()


def test_existing_template_is_never_overwritten(collection):
    destination = new_template.create_template("python-lib", root=collection)
    marker = destination / "cookiecutter.json"
    marker.write_text("Keep my changes\n")
    with pytest.raises(FileExistsError):
        new_template.create_template("python-lib", root=collection)
    assert marker.read_text() == "Keep my changes\n"


@pytest.mark.parametrize("name", ["../outside", "/tmp/outside", "bad/name", "Bad Name", ""])
def test_invalid_names_cannot_escape_src(name, collection):
    with pytest.raises(argparse.ArgumentTypeError):
        new_template.create_template(name, root=collection)


def test_render_failure_leaves_no_template(collection):
    with (
        patch.object(new_template, "cookiecutter", side_effect=OSError("Render failed")),
        pytest.raises(OSError, match="Render failed"),
    ):
        new_template.create_template("python-lib", root=collection)
    assert not (collection / "src/python-lib").exists()
    assert not list((collection / "src").glob(".new-template-*"))


@pytest.mark.parametrize(
    "github,sourcecraft", [("yes", "no"), ("no", "yes"), ("yes", "yes"), ("no", "no")]
)
def test_seed_preserves_github_and_sourcecraft_support(
    github, sourcecraft, collection, tmp_path, cookiecutter_config
):
    new_template.create_template("custom", root=collection)
    project = render(
        collection,
        "custom",
        tmp_path,
        cookiecutter_config,
        ci_github=github,
        ci_sourcecraft=sourcecraft,
    )
    for directory, enabled, filename in (
        (".github", github, "workflows/ci.yml"),
        (".sourcecraft", sourcecraft, "ci.yaml"),
    ):
        assert (project / directory).exists() == (enabled == "yes")
        if enabled == "yes":
            configuration = (project / directory / filename).read_text()
            yaml.safe_load(configuration)
            assert "make check" in configuration


@pytest.mark.parametrize("enabled", ["yes", "no"])
def test_base_ci_selection_is_preserved(enabled, tmp_path, cookiecutter_config):
    project = render(
        ROOT,
        "base",
        tmp_path,
        cookiecutter_config,
        ci_github=enabled,
        ci_sourcecraft=enabled,
        ci_gitlab=enabled,
    )
    for filename in (".github", ".sourcecraft", ".gitlab-ci.yml"):
        assert (project / filename).exists() == (enabled == "yes")
