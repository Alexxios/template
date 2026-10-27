"""Exercise native Pants inference and the actual CI matrix step."""

import json
import os
import re
import shutil
import subprocess

import pytest

from .scaffold import scaffold
from .test_web import generate, run_just, workflow
from .test_web import project as project


def test_scaffolds_use_native_build_files_without_a_generated_graph(project):
    assert not (project / "scripts/workspace.py").exists()
    assert not (project / "BUILD.workspace").exists()
    for kind, group in (("service", "services"), ("lib", "libs")):
        assert generate(project, kind, kind).returncode == 0
        assert (project / group / kind / "BUILD").is_file()
    assert run_just(project, "check-generated").returncode == 0


@pytest.fixture
def repository(project):
    if shutil.which("pants") is None:
        pytest.skip("Install the Pants launcher for engine integration")
    scaffold(project)
    for args in (
        ["init", "-b", "main"],
        ["add", "."],
        [
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "Fixture",
        ],
    ):
        subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
    return project


def matrix(project, *, since="HEAD", publish=False):
    step = next(
        step
        for step in workflow(project, "checks")["jobs"]["discover"]["steps"]
        if step.get("id") == "members"
    )
    output = project.parent / "github-output"
    output.write_text("")
    result = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", step["run"]],
        cwd=project,
        env={
            **os.environ,
            "CHANGED_SINCE": since,
            "PUBLISH": str(publish).lower(),
            "GITHUB_OUTPUT": str(output),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    value = json.loads(output.read_text().removeprefix("matrix="))
    assert all(row["id"] == row["path"].replace("/", "-") for row in value["include"])
    return [row["path"] for row in value["include"]]


ALL_SCOPES = ["integration", "libs/shared_utils", "libs/storage", "services/api", "services/worker"]


@pytest.mark.parametrize(
    "filename, expected",
    [
        (None, ["integration"]),
        ("libs/storage/src/storage/status.py", ["integration", "libs/storage", "services/worker"]),
        ("services/api/src/api/main.py", ["integration", "services/api"]),
        ("libs/shared_utils/pyproject.toml", ALL_SCOPES),
        ("libs/shared_utils/new_asset.txt", ALL_SCOPES),
        ("uv.lock", ALL_SCOPES),
        ("tests/test_workspace.py", ["integration"]),
    ],
)
def test_native_changed_selection(repository, filename, expected):
    if filename:
        path = repository / filename
        path.write_text((path.read_text() if path.exists() else "") + "\n# change\n")
    assert matrix(repository) == expected


@pytest.mark.parametrize("change", ["delete", "rename", "publish"])
def test_deletions_renames_and_publication_select_every_member(repository, change):
    path = repository / "libs/storage/src/storage/status.py"
    if change == "delete":
        path.unlink()
    elif change == "rename":
        path.rename(path.with_name("renamed.py"))
    assert matrix(repository, publish=change == "publish") == ALL_SCOPES


def test_native_queries_follow_imports_without_codegen(repository):
    def query(goal, spec):
        result = subprocess.run(
            ["pants", goal, "--transitive", spec],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return set(re.findall(r"^(?:services|libs)/[^/:]+", result.stdout, re.MULTILINE))

    assert query("dependencies", "services/worker:member") == {
        "services/worker",
        "libs/storage",
        "libs/shared_utils",
    }
    assert query("dependents", "libs/shared_utils::") == {
        "services/api",
        "services/worker",
        "libs/storage",
    }
    # Adding an import changes the graph immediately, without a manifest/codegen pass.
    path = repository / "services/api/src/api/main.py"
    path.write_text(path.read_text() + "\nimport storage.status\n")
    assert "services/api" in query("dependents", "libs/storage::")


def test_empty_workspace_matrix(project):
    if shutil.which("pants") is None:
        pytest.skip("Install the Pants launcher for engine integration")
    assert matrix(project, since="") == ["integration"]
