"""Create a service or library from the project's package template."""

from __future__ import annotations

import argparse
import keyword
import re
import tempfile
import tomllib
from pathlib import Path

from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter

ROOT = Path(__file__).resolve().parents[1]


def create_member(kind: str, name: str, description: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        raise ValueError("Use a lowercase Python package name, such as billing_api.")
    destination = ROOT / ("services" if kind == "service" else "libs") / name
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    names = {re.sub(r"[-_.]+", "-", project["name"].lower())}
    for group in ("services", "libs"):
        for manifest in (ROOT / group).glob("*/pyproject.toml"):
            member = tomllib.loads(manifest.read_text())["project"]
            names.add(re.sub(r"[-_.]+", "-", member["name"].lower()))
        candidate = ROOT / group / name
        if candidate.exists() or candidate.is_symlink():
            raise ValueError(f"A workspace member named {name!r} already exists.")
    if re.sub(r"[-_.]+", "-", name) in names:
        raise ValueError(f"A workspace project named {name!r} already exists.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".new-member-", dir=destination.parent) as temporary:
        generated = cookiecutter(
            str(ROOT / "templates/member"),
            no_input=True,
            output_dir=temporary,
            extra_context={"package_name": name, "description": description, "_kind": kind},
        )
        Path(generated).rename(destination)
    return destination


def main(kind: str) -> None:
    parser = argparse.ArgumentParser(description=f"Create a workspace {kind}.")
    parser.add_argument("name", help="Python package name, such as billing_api")
    parser.add_argument("--description", default=f"A workspace {kind}")
    args = parser.parse_args()
    try:
        destination = create_member(kind, args.name, args.description)
    except (ValueError, OSError, CookiecutterException) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Created {destination}. Run make bootstrap to install workspace members.")
