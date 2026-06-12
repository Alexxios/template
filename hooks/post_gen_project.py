"""Post-generation hook: build tox matrix and optionally git init."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path.cwd()

PYTHON_MIN = "{{cookiecutter.python_min_version}}"
PYTHON_MAX = "{{cookiecutter.python_version}}"
INIT_GIT = "{{cookiecutter.init_git}}" == "yes"


def _parse(v: str) -> tuple[int, int]:
    major, minor = v.split(".")[:2]
    return int(major), int(minor)


def build_factor_list() -> str:
    lo_major, lo_minor = _parse(PYTHON_MIN)
    hi_major, hi_minor = _parse(PYTHON_MAX)
    if (lo_major, lo_minor) > (hi_major, hi_minor):
        lo_minor, hi_minor = hi_minor, lo_minor
        lo_major, hi_major = hi_major, lo_major
    if lo_major != hi_major:
        sys.exit(
            f"ERROR: python_min_version ({PYTHON_MIN}) and python_version "
            f"({PYTHON_MAX}) must share a major version."
        )
    factors = [f"py{lo_major}{minor}" for minor in range(lo_minor, hi_minor + 1)]
    return ", ".join(factors)


def patch_tox() -> None:
    tox = PROJECT_DIR / "tox.ini"
    text = tox.read_text()
    tox.write_text(text.replace("__PY_FACTORS__", build_factor_list()))


def init_git() -> None:
    try:
        subprocess.run(["git", "init", "-q"], check=True, cwd=PROJECT_DIR)
        subprocess.run(["git", "add", "."], check=True, cwd=PROJECT_DIR)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit from cookiecutter template"],
            check=True,
            cwd=PROJECT_DIR,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"WARN: git init skipped ({e})", file=sys.stderr)


def main() -> None:
    patch_tox()
    if INIT_GIT:
        init_git()


if __name__ == "__main__":
    main()
