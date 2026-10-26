"""Create a selectable Cookiecutter template from an existing starter."""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*")


def template_name(value: str) -> str:
    if not NAME_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "Use a lowercase name such as python-lib, with letters, numbers, '-' or '_'."
        )
    return value


def create_template(name: str, source: str = "base", *, root: Path = ROOT) -> Path:
    """Copy the starter without rendering its Jinja expressions or overwriting files."""
    template_name(name)
    template_name(source)
    templates = root / "src"
    starter = templates / source
    destination = templates / name
    if not (starter / "cookiecutter.json").is_file():
        raise FileNotFoundError(f"No template found at {starter}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Template already exists: {destination}")

    # Stage the copy so a failed operation cannot leave a partial template.
    with tempfile.TemporaryDirectory(prefix=".new-template-", dir=templates) as temporary:
        staged = Path(temporary) / name
        shutil.copytree(
            starter,
            staged,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache"
            ),
        )
        staged.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", type=template_name, help="New template directory under src/")
    parser.add_argument(
        "--from", dest="source", type=template_name, default="base", help="Starter template (base)"
    )
    args = parser.parse_args()
    try:
        destination = create_template(args.name, args.source)
    except OSError as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Created {destination.relative_to(ROOT)}/")
    print("Customize its cookiecutter.json, hooks/, and {{cookiecutter.project_slug}}/.")
    print(f"Generate a project: cookiecutter . --directory src/{args.name}")


if __name__ == "__main__":
    main()
