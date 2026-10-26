"""Check workflow selection and inner CI exit-status propagation without a remote."""

import os
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("template", ["base", "webapp"])
@pytest.mark.parametrize("event", ["push", "pull_request"])
@pytest.mark.parametrize("inner_status", [0, 1])
def test_wait_selects_generated_commit_and_propagates_failure(
    tmp_path, template, event, inner_status
):
    workflow = yaml.safe_load((ROOT / f".github/workflows/validate-{template}.yml").read_text())
    config = tomllib.loads((ROOT / f"tests/{template}/validation.toml").read_text())
    expected = config["github"][f"{event}_workflow"]
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
        if step.get("id") in {"collect", "artifact"} or step.get("name", "").startswith("Delete"):
            assert "always()" in step["if"]
