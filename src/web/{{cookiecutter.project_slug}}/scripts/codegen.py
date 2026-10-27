"""Render the workspace README from its Jinja source and current members."""

from __future__ import annotations

import argparse
import re
import tempfile
import tomllib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

ROOT = Path(__file__).resolve().parents[1]


def members(root: Path = ROOT) -> list[Path]:
    return [
        path.parent
        for group in ("services", "libs")
        for path in sorted((root / group).glob("*/pyproject.toml"))
        if not path.parent.name.startswith(".")
    ]


def context(root: Path = ROOT) -> dict:
    config = tomllib.loads((root / "pyproject.toml").read_text())
    repository = config["tool"]["codegen"]["github_repository"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("tool.codegen.github_repository must be a GitHub owner/repository")
    owner, name = repository.split("/")
    pages_url = f"https://{owner.lower()}.github.io"
    if name.lower() != f"{owner.lower()}.github.io":
        pages_url += f"/{name}"
    grouped = {"services": [], "libs": []}
    for member in members(root):
        grouped[member.parent.name].append(
            {"name": member.name, "path": member.relative_to(root).as_posix()}
        )
    return {
        "project": config["project"],
        "github_repository": repository,
        "pages_url": pages_url,
        **grouped,
    }


def sync(root: Path = ROOT, *, check: bool = False) -> list[Path]:
    environment = Environment(
        loader=FileSystemLoader(root / "templates/readme"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    rendered = environment.get_template("README.md.jinja").render(**context(root))
    readme = root / "README.md"
    if readme.exists() and readme.read_text() == rendered:
        return []
    if not check:
        # Replace only after rendering succeeds, leaving the old README intact on failure.
        with tempfile.TemporaryDirectory(prefix=".codegen-", dir=root) as directory:
            temporary = Path(directory) / "README.md"
            temporary.write_text(rendered)
            temporary.replace(readme)
    return [readme]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing files")
    args = parser.parse_args()
    try:
        changed = sync(check=args.check)
    except (ValueError, OSError, KeyError, TemplateError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    for path in changed:
        print(f"{'Out of date' if args.check else 'Generated'}: {path.relative_to(ROOT)}")
    if args.check and changed:
        parser.exit(1, "Run make codegen and commit the generated README.\n")


if __name__ == "__main__":
    main()
