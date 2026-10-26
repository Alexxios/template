"""Exercise the base template's nested Python package generator."""

import subprocess
import sys
from pathlib import Path


def scaffold(project: Path) -> None:
    for name in ("pkg_alpha", "pkg_beta", "pkg_gamma"):
        subprocess.run(
            [
                sys.executable,
                str(project / "scripts/new_package.py"),
                "--no-input",
                f"package_name={name}",
            ],
            cwd=project,
            check=True,
        )
        for relative in (
            f"src/{name}/__init__.py",
            f"src/{name}/py.typed",
            f"tests/{name}/test_smoke.py",
        ):
            if not (project / relative).is_file():
                raise RuntimeError(f"Missing generated file: {relative}")
        if (project / f"tests/{name}/__init__.py").exists():
            raise RuntimeError("Generated tests must use importlib discovery without __init__.py")
