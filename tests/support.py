"""Shared CLI for template-owned fixtures: render a project, then scaffold it."""

import argparse
import tomllib
from collections.abc import Callable
from pathlib import Path

from cookiecutter.main import cookiecutter


def main(package: Path, scaffold: Callable[[Path], None]) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    render = subparsers.add_parser("render", help="Render a project with the selected inner CI")
    render.add_argument("project", type=Path)
    render.add_argument("--ci", choices=("github", "sourcecraft"), default="github")
    fixture = subparsers.add_parser("scaffold", help="Add this template's integration fixture")
    fixture.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    if args.command == "scaffold":
        if not (project / "pyproject.toml").is_file():
            parser.error(f"Render the project first: {project}")
        scaffold(project)
        return

    config = tomllib.loads((package / "validation.toml").read_text())
    cookiecutter(
        str(package.parents[1]),
        directory=f"src/{config['template']}",
        no_input=True,
        output_dir=str(project.parent),
        extra_context={
            "project_name": "CI Test Project",
            **config.get("context", {}),
            "project_slug": project.name,
            "ci_github": "yes" if args.ci == "github" else "no",
            "ci_sourcecraft": "yes" if args.ci == "sourcecraft" else "no",
            "ci_gitlab": "no",
            "init_git": "no",
        },
    )
    print(project)
