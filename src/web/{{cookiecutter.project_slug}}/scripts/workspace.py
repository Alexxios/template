"""Discover workspace members for README generation, local commands, and the CI matrix."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def members(root: Path = ROOT) -> list[Path]:
    paths = [
        path.parent
        for group in ("services", "libs")
        for path in sorted((root / group).glob("*/pyproject.toml"))
        if not path.parent.name.startswith(".")
    ]
    for path in paths:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", path.name):
            raise ValueError(f"Invalid member directory: {path.relative_to(root)}")
    return paths


def scopes() -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in members()] + ["integration"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", action="store_true")
    args = parser.parse_args()
    paths = scopes()
    if args.matrix:
        print(
            json.dumps(
                {"include": [{"path": path, "id": path.replace("/", "-")} for path in paths]}
            )
        )
    else:
        print("\n".join(paths))
