"""Exercise video attachment timing and scope isolation without requiring a browser."""

import json

import allure
import pytest

from .test_web import generate, run_just
from .test_web import project as project

ARTIFACT_FIXTURE = """\
from pathlib import Path

import pytest


@pytest.fixture
def output_path(request):
    directory = Path(request.config.getoption("--output")) / request.node.name
    yield str(directory)
    # Model videos becoming available only after browser-context teardown.
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "first.webm").write_bytes(b"first video")
    (directory / "second.webm").write_bytes(b"second video")
    (directory / "screenshot.png").write_bytes(b"not a video")


@pytest.fixture
def setup_error(output_path):
    raise RuntimeError("setup failed")


@pytest.fixture
def teardown_error(output_path):
    yield
    raise RuntimeError("teardown failed")
"""

VIDEO_TESTS = """\
import pytest


def test_pass(output_path):
    pass


def test_call_failure(output_path):
    assert False, "call failed"


def test_setup_failure(setup_error):
    pass


def test_teardown_failure(teardown_error):
    pass


def test_skip(output_path):
    pytest.skip("not applicable")


def test_without_browser():
    pass
"""


def write_video_suite(project, scope):
    if scope == "integration":
        tests = project / "tests"
    else:
        group, name = scope.split("/")
        result = generate(project, "service" if group == "services" else "lib", name)
        assert result.returncode == 0, result.stdout + result.stderr
        tests = project / scope / "tests"
    (tests / "conftest.py").write_text(ARTIFACT_FIXTURE)
    (tests / "test_videos.py").write_text(VIDEO_TESTS)


def allure_results(project, scope):
    return {
        result["name"]: result
        for path in (project / "reports" / scope / "allure-results").glob("*-result.json")
        if (result := json.loads(path.read_text()))
    }


@allure.feature("Playwright failure videos")
@allure.title("Attach finalized videos to failures in {scope}")
@pytest.mark.parametrize("scope", ["integration", "services/frontend", "libs/widgets"])
def test_videos_attach_only_to_their_failed_test_after_teardown(project, scope):
    write_video_suite(project, scope)
    other = project / "reports/services/other/playwright/previous.webm"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"another scope")

    result = run_just(project, "test", scope)
    assert result.returncode == 1, result.stdout + result.stderr
    results = allure_results(project, scope)
    failed = {"test_call_failure", "test_setup_failure", "test_teardown_failure"}
    assert failed <= results.keys()
    for name, report in results.items():
        videos = [a for a in report.get("attachments", []) if a["type"] == "video/webm"]
        assert len(videos) == (2 if name in failed else 0), report
        for attachment in videos:
            copied = project / "reports" / scope / "allure-results" / attachment["source"]
            original = project / "reports" / scope / "playwright" / name / attachment["name"]
            assert copied.read_bytes() == original.read_bytes()
    assert other.read_bytes() == b"another scope"
    assert not list(project.glob("**/test-results"))


@allure.feature("Playwright failure videos")
@allure.title("Attachment errors preserve test failures and allow later tests to finish")
def test_attachment_error_does_not_abort_the_test_run(project):
    write_video_suite(project, "integration")
    fixture = project / "tests/conftest.py"
    fixture.write_text(
        fixture.read_text() + "\nimport allure\n\n"
        "def fail_attachment(*args, **kwargs):\n"
        '    Path("attachment-attempted").touch()\n'
        '    raise OSError("cannot copy video")\n\n'
        "allure.attach.file = fail_attachment\n"
    )
    result = run_just(project, "test", "integration")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "INTERNALERROR" not in result.stdout + result.stderr
    assert (project / "attachment-attempted").exists()
    reports = allure_results(project, "integration")
    assert reports["test_call_failure"]["status"] == "failed"
    assert reports["test_without_browser"]["status"] == "passed"


@allure.feature("Playwright failure videos")
@allure.title("A tool startup failure clears stale videos only from the selected scope")
def test_tool_failure_clears_old_videos_without_touching_other_scopes(project):
    assert generate(project, "service", "frontend").returncode == 0
    videos = []
    for scope in ("services/frontend", "integration"):
        path = project / "reports" / scope / "playwright/previous.webm"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"old video")
        videos.append(path)
    result = run_just(project, "test", "services/frontend", env={"SCOPE_PYTHON": "false"})
    assert result.returncode != 0
    assert not videos[0].exists()
    assert videos[1].read_bytes() == b"old video"
