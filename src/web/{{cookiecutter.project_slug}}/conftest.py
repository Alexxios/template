"""Attach finalized Playwright failure videos to the current Allure test."""

import logging
from pathlib import Path

import allure
import pytest

FAILED = pytest.StashKey[bool]()
VIDEO_OUTPUT = pytest.StashKey[Path]()
LOGGER = logging.getLogger(__name__)


@pytest.hookimpl(wrapper=True)
def pytest_fixture_setup(fixturedef, request):
    value = yield
    if fixturedef.argname == "output_path":
        # A later setup failure can leave this fixture out of item.funcargs.
        request.node.stash[VIDEO_OUTPUT] = Path(value)
    return value


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(item):
    # Run after Playwright's report hook, which can finalize retained artifacts.
    report = yield
    if report.when == "setup":
        item.stash[FAILED] = False
    item.stash[FAILED] = item.stash.get(FAILED, False) or report.failed
    if report.when == "teardown":
        output = item.stash.get(VIDEO_OUTPUT, None)
        if output is not None:
            del item.stash[VIDEO_OUTPUT]
        if output is not None and item.stash[FAILED]:
            try:
                for video in sorted(output.glob("*.webm")):
                    if video.is_file():
                        allure.attach.file(
                            video,
                            name=video.name,
                            attachment_type=allure.attachment_type.WEBM,
                        )
            except Exception:
                # Diagnostics must not replace the original test failure.
                LOGGER.warning("Could not attach video for %s", item.nodeid, exc_info=True)
    return report
