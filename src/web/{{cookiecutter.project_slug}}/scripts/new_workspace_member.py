"""Create a service or library and regenerate the workspace README."""

from __future__ import annotations

import argparse
import keyword
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

from codegen import context, sync
from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter
from jinja2 import TemplateError

ROOT = Path(__file__).resolve().parents[1]


def create_member(kind: str, name: str, description: str) -> Path:
    if kind not in {"service", "lib"}:
        raise ValueError(f"Unknown workspace member kind: {kind!r}")
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
    reports_url = context(ROOT)["reports_url"]
    with tempfile.TemporaryDirectory(prefix=".new-member-", dir=destination.parent) as temporary:
        generated = cookiecutter(
            str(ROOT / "templates" / kind),
            no_input=True,
            output_dir=temporary,
            extra_context={
                "package_name": name,
                "description": description,
                "reports_url": reports_url,
            },
        )
        Path(generated).rename(destination)
    try:
        sync(ROOT)
    except ValueError, OSError, KeyError, TemplateError:
        shutil.rmtree(destination)
        raise
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("service", "lib"))
    parser.add_argument("name", help="Python package name, such as billing_api")
    parser.add_argument("--description")
    args = parser.parse_args()
    try:
        destination = create_member(
            args.kind, args.name, args.description or f"A workspace {args.kind}"
        )
    except (ValueError, OSError, KeyError, TemplateError, CookiecutterException) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Created {destination}. Run make bootstrap to install workspace members.")


if __name__ == "__main__":
    main()
