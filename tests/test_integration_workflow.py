"""Check workflow selection and inner CI exit-status propagation without a remote."""

import os
import subprocess
import tarfile
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("template", ["base", "web"])
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


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_web_collects_pages_or_pr_reports_without_deploying(tmp_path, event):
    workflow = yaml.safe_load((ROOT / ".github/workflows/validate-web.yml").read_text())
    assert "publish-reports" not in workflow["jobs"]
    steps = workflow["jobs"]["validate"]["steps"]
    collect = next(step for step in steps if step.get("id") == "collect")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    if event == "push":
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
    config = tomllib.loads((ROOT / "tests/web/validation.toml").read_text())["github"]
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
        },
        check=True,
        capture_output=True,
        text=True,
    )
    assert f"--name {artifact}" in calls.read_text()
    collected = tmp_path / "generated-ci/reports"
    if event == "push":
        assert artifact == "github-pages"
        assert (collected / "index.html").read_text() == "Documentation"
        assert (collected / "reports/junit.xml").is_file()
        assert "pages-ready=true" in output.read_text()
    else:
        assert artifact == "check-reports"
        assert (collected / "junit.xml").is_file()
        assert not output.read_text()
