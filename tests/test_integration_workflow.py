"""Check workflow selection and inner CI exit-status propagation without a remote."""

import os
import subprocess
import tarfile
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validation_workflow(template):
    caller = yaml.safe_load((ROOT / f".github/workflows/validate-{template}.yml").read_text())
    job = caller["jobs"]["validate"]
    workflow = yaml.safe_load((ROOT / job["uses"]).read_text())
    assert job["with"]["template"] == template
    assert job["secrets"] == {"CI_GITHUB_TOKEN": "${{ secrets.CI_GITHUB_TOKEN }}"}
    return workflow, job["with"]


@pytest.mark.parametrize("template", ["base", "web"])
def test_generated_callers_match_reusable_workflow_inputs(template):
    workflow, inputs = validation_workflow(template)
    # BaseLoader keeps "on" as a string rather than a YAML 1.1 boolean.
    definition = yaml.load(
        (ROOT / ".github/workflows/template-validation.yml").read_text(), Loader=yaml.BaseLoader
    )["on"]["workflow_call"]
    assert set(inputs) == set(definition["inputs"])
    for name, value in inputs.items():
        expected = bool if definition["inputs"][name]["type"] == "boolean" else str
        assert isinstance(value, expected)
    config = tomllib.loads((ROOT / f"tests/{template}/validation.toml").read_text())["github"]
    assert all(inputs[key] == value for key, value in config.items() if key in inputs)
    env = workflow["jobs"]["validate"]["env"]
    assert env["TEMPLATE_MODULE"] == "tests.${{ inputs.package }}"
    for name in ("INNER_WORKFLOW", "INNER_ARTIFACT"):
        assert "github.event_name == 'pull_request'" in env[name]


@pytest.mark.parametrize("event", ["push", "workflow_dispatch", "pull_request"])
@pytest.mark.parametrize("enable_pages", [True, False])
def test_trigger_enables_pages_only_for_configured_non_pr_runs(tmp_path, event, enable_pages):
    workflow, _ = validation_workflow("base")
    trigger = next(
        step
        for step in workflow["jobs"]["validate"]["steps"]
        if step.get("name") == "Trigger generated project's CI"
    )
    for name in ("git", "gh"):
        command = tmp_path / name
        command.write_text(f'#!/bin/sh\nprintf "%s\\n" "{name} $*" >> "$CALL_LOG"\n')
        command.chmod(0o755)
    calls = tmp_path / "calls"
    subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", trigger["run"]],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CALL_LOG": str(calls),
            "GITHUB_EVENT_NAME": event,
            "ENABLE_PAGES": str(enable_pages).lower(),
            "GH_REPO": "example/temporary",
        },
        check=True,
        capture_output=True,
        text=True,
    )
    commands = calls.read_text()
    assert ("gh api --method POST" in commands) == (enable_pages and event != "pull_request")
    branch = "ci-checks" if event == "pull_request" else "main"
    assert f"git push origin HEAD:refs/heads/{branch}" in commands
    assert ("gh pr create" in commands) == (event == "pull_request")


@pytest.mark.parametrize("template", ["base", "web"])
@pytest.mark.parametrize("event", ["push", "pull_request"])
@pytest.mark.parametrize("inner_status", [0, 1])
def test_wait_selects_generated_commit_and_propagates_failure(
    tmp_path, template, event, inner_status
):
    workflow, inputs = validation_workflow(template)
    config = tomllib.loads((ROOT / f"tests/{template}/validation.toml").read_text())
    expected = config["github"][f"{event}_workflow"]
    assert inputs[f"{event}_workflow"] == expected
    steps = workflow["jobs"]["validate"]["steps"]
    wait = next(step for step in steps if step.get("id") == "wait")
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
        'case "$2" in\n'
        "  list) echo 123 ;;\n"
        '  watch) exit "$INNER_STATUS" ;;\n'
        "  *) exit 99 ;;\n"
        "esac\n"
    )
    fake_gh.chmod(0o755)
    timeout = tmp_path / "timeout"
    timeout.write_text('#!/bin/sh\nshift\nexec "$@"\n')
    timeout.chmod(0o755)
    output = tmp_path / "output"
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", wait["run"]],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "INNER_WORKFLOW": expected,
            "GITHUB_EVENT_NAME": event,
            "GITHUB_OUTPUT": str(output),
            "GH_REPO": "example/temporary",
            "GENERATED_COMMIT": "abc123",
            "CALL_LOG": str(calls),
            "INNER_STATUS": str(inner_status),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == inner_status, result.stderr
    assert output.read_text() == "run_id=123\n"
    branch = "ci-checks" if event == "pull_request" else "main"
    assert (
        f"--workflow {expected} --branch {branch} --event {event} --commit abc123"
        in calls.read_text()
    )
    assert "--exit-status" in calls.read_text()
    # Logs, reports, and cleanup must still run after a failed inner workflow.
    for step in steps:
        if step.get("id") in {"collect", "documentation", "artifact"} or step.get(
            "name", ""
        ).startswith("Delete"):
            assert "always()" in step["if"]


@pytest.mark.parametrize("event", ["push", "pull_request"])
@pytest.mark.parametrize("template", ["base", "web"])
@pytest.mark.parametrize("artifact_format", ["pages", "directory"])
def test_collects_pages_or_pr_reports_without_deploying(tmp_path, event, template, artifact_format):
    workflow, inputs = validation_workflow(template)
    assert "publish-reports" not in workflow["jobs"]
    steps = workflow["jobs"]["validate"]["steps"]
    trigger = next(step for step in steps if step.get("name") == "Trigger generated project's CI")
    assert 'gh api --method POST "repos/$GH_REPO/pages" -f build_type=workflow' in trigger["run"]
    collect = next(step for step in steps if step.get("id") == "collect")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    if event == "push" and artifact_format == "pages":
        site = tmp_path / "site"
        site.mkdir()
        (site / "index.html").write_text("Documentation")
        (site / "reports").mkdir()
        (site / "reports/junit.xml").write_text("<testsuites/>")
        with tarfile.open(fixture / "artifact.tar", "w") as archive:
            archive.add(site, arcname=".")
    else:
        (fixture / "junit.xml").write_text("<testsuites/>")
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
        'if [ "$2" = view ]; then echo "Inner CI log"; exit 0; fi\n'
        'while [ "$#" -gt 0 ]; do\n'
        '  if [ "$1" = --dir ]; then\n'
        '    shift; mkdir -p "$1"; cp -R "$FIXTURE/." "$1/"; exit 0\n'
        "  fi\n"
        "  shift\n"
        "done\n"
        "exit 1\n"
    )
    fake_gh.chmod(0o755)
    config = tomllib.loads((ROOT / f"tests/{template}/validation.toml").read_text())["github"]
    artifact = config[f"{event}_artifact"]
    calls = tmp_path / "calls"
    output = tmp_path / "output"
    output.touch()
    subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", collect["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CALL_LOG": str(calls),
            "FIXTURE": str(fixture),
            "GITHUB_EVENT_NAME": event,
            "GITHUB_OUTPUT": str(output),
            "GH_REPO": "example/temporary",
            "RUN_ID": "123",
            "RUNNER_TEMP": str(tmp_path),
            "INNER_ARTIFACT": artifact,
            "PUSH_ARTIFACT_FORMAT": artifact_format,
        },
        check=True,
        capture_output=True,
        text=True,
    )
    assert f"--name {artifact}" in calls.read_text()
    collected = tmp_path / "generated-ci/reports"
    if event == "push" and artifact_format == "pages":
        assert artifact == "github-pages"
        assert (collected / "index.html").read_text() == "Documentation"
        assert (collected / "reports/junit.xml").is_file()
    else:
        if event == "pull_request":
            assert artifact == "check-reports"
        assert (collected / "junit.xml").is_file()
        assert not output.read_text()

    documentation = next(step for step in steps if step.get("id") == "documentation")
    assert "github.event_name != 'pull_request'" in documentation["if"]
    assert steps.index(documentation) < next(
        i for i, step in enumerate(steps) if step.get("id") == "artifact"
    )
    if event == "push":
        (fixture / "index.html").write_text("Built MkDocs site")
        subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", documentation["run"]],
            cwd=tmp_path,
            env={
                **os.environ,
                "PATH": f"{tmp_path}:{os.environ['PATH']}",
                "CALL_LOG": str(calls),
                "FIXTURE": str(fixture),
                "GH_REPO": "example/temporary",
                "RUN_ID": "123",
                "RUNNER_TEMP": str(tmp_path),
                "DOCUMENTATION_ARTIFACT": inputs["documentation_artifact"],
            },
            check=True,
            capture_output=True,
            text=True,
        )
        assert "--name documentation" in calls.read_text()
        assert (tmp_path / "generated-ci/docs/index.html").read_text() == "Built MkDocs site"
