"""Check which template validations are selected by generated path filters."""

from pathlib import Path, PurePosixPath

import pytest
import yaml

from scripts.new_template import create_template

ROOT = Path(__file__).resolve().parents[1]


def triggers(path):
    # BaseLoader preserves the YAML key "on" instead of treating it as a boolean.
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)["on"]


def validation_paths(root, provider, event, templates):
    if provider == "github":
        return {
            name: triggers(root / f".github/workflows/validate-{name}.yml")[event]["paths"]
            for name in templates
        }
    return {
        name: entry["filter"]["paths"]
        for entry in triggers(root / ".sourcecraft/ci.yaml")[event]
        for name in templates
        if entry["workflows"] == [f"validate-{name}"]
    }


def selected(paths, changes):
    return {
        name
        for name, patterns in paths.items()
        if any(PurePosixPath(path).full_match(pattern) for path in changes for pattern in patterns)
    }


@pytest.mark.parametrize("provider", ["github", "sourcecraft"])
@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_only_affected_templates_are_selected(provider, event):
    paths = validation_paths(ROOT, provider, event, ["base", "web"])
    both = {"base", "web"}
    cases = [
        (["src/base/cookiecutter.json"], {"base"}),
        (["src/web/{{cookiecutter.project_slug}}/.github/workflows/ci.yml"], {"web"}),
        (["tests/base/scaffold.py"], {"base"}),
        (["tests/web/validation.toml", ".sourcecraft/ci.yaml"], {"web"}),
        (["src/base/hooks/post_gen_project.py", "tests/web/scaffold.py"], both),
        (["README.md", "LICENSE", "docs/usage.md"], set()),
        (["templates/cookiecutter/cookiecutter.json"], set()),
        (["templates/validation/package/scaffold.py.jinja"], set()),
        (["tests/support.py"], both),
        (["tests/__init__.py"], both),
        (["scripts/sync_templates.py"], both),
        (["pyproject.toml"], both),
        (["uv.lock"], both),
        ([".python-version"], both),
        (["templates/validation/github.yml.jinja"], both if provider == "github" else set()),
        (
            ["templates/validation/sourcecraft.yaml.jinja"],
            both if provider == "sourcecraft" else set(),
        ),
        (["scripts/sourcecraft_repo.py"], both if provider == "sourcecraft" else set()),
        ([".github/workflows/validate-web.yml"], {"web"} if provider == "github" else set()),
        ([], set()),
    ]
    for changes, expected in cases:
        assert selected(paths, changes) == expected, (provider, event, changes)


def test_repository_checks_and_manual_github_runs_remain_unfiltered():
    github = triggers(ROOT / ".github/workflows/ci.yml")
    for event in ("push", "pull_request"):
        assert "paths" not in (github[event] or {})
    for name in ("base", "web"):
        workflow = triggers(ROOT / f".github/workflows/validate-{name}.yml")
        assert "workflow_dispatch" in workflow
        assert workflow["push"]["branches"] == ["main", "master"]
    sourcecraft = triggers(ROOT / ".sourcecraft/ci.yaml")
    for event in ("push", "pull_request"):
        checks = next(
            entry for entry in sourcecraft[event] if "check-repository" in entry["workflows"]
        )
        assert "paths" not in checks.get("filter", {})
        for entry in sourcecraft[event]:
            assert len(entry["workflows"]) == 1
            if event == "push":
                assert entry["filter"]["branches"] == ["main", "master"]


def test_new_templates_receive_filters_for_their_normalized_fixture_package(collection):
    create_template("python-lib", root=collection)
    for provider in ("github", "sourcecraft"):
        for event in ("push", "pull_request"):
            paths = validation_paths(collection, provider, event, ["python-lib"])
            assert selected(paths, ["src/python-lib/cookiecutter.json"]) == {"python-lib"}
            assert selected(paths, ["tests/python_lib/scaffold.py"]) == {"python-lib"}
            assert not selected(paths, ["src/web/cookiecutter.json", "tests/web/scaffold.py"])
