"""Create a selectable template from the tooling seed in templates/cookiecutter."""

from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

from cookiecutter.exceptions import CookiecutterException
from cookiecutter.main import cookiecutter

ROOT = Path(__file__).resolve().parents[1]
NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*")


def template_name(value: str) -> str:
    if not NAME_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "Use a lowercase name such as python-lib, with letters, numbers, '-' or '_'."
        )
    return value


def create_template(name: str, *, root: Path = ROOT) -> Path:
    """Render the metatemplate, preserving the new template's project expressions."""
    template_name(name)
    templates = root / "src"
    starter = root / "templates" / "cookiecutter"
    destination = templates / name
    if not (starter / "cookiecutter.json").is_file():
        raise FileNotFoundError(f"No template found at {starter}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Template already exists: {destination}")

    templates.mkdir(exist_ok=True)
    # Stage generation so failures cannot leave a partial template in src/.
    with tempfile.TemporaryDirectory(prefix=".new-template-", dir=templates) as temporary:
        staged = Path(
            cookiecutter(
                str(starter),
                no_input=True,
                output_dir=temporary,
                extra_context={"template_name": name},
            )
        )
        staged.rename(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", type=template_name, help="New template directory under src/")
    args = parser.parse_args()
    try:
        destination = create_template(args.name)
    except (OSError, CookiecutterException) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Created {destination.relative_to(ROOT)}/")
    print(
        "Add your project layout to {{cookiecutter.project_slug}}/ and customize cookiecutter.json."
    )
    print(f"Generate a project: cookiecutter . --directory src/{args.name}")


if __name__ == "__main__":
    main()
