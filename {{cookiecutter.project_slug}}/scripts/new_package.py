"""Scaffold a new package under src/ and tests/.

Wraps the inner cookiecutter at ``templates/package/``: generates into a temp
dir, moves the rendered ``src/<pkg>`` and ``tests/<pkg>`` into the project.

With setuptools auto-discovery (``packages.find`` with ``where = ["src"]``),
no manual ``pyproject.toml`` registration is needed — packages are found
under ``src/`` automatically.

Usage:
    uv run python scripts/new_package.py
    uv run python scripts/new_package.py --no-input package_name=my_pkg
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "package"


def render_to_tempdir(extra_args: list[str]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="new_pkg_"))
    cmd = [sys.executable, "-m", "cookiecutter", str(TEMPLATE), "-o", str(tmp), *extra_args]
    subprocess.run(cmd, check=True)
    (holder,) = list(tmp.iterdir())
    return holder


def relocate(holder: Path) -> str:
    (pkg_dir,) = list((holder / "src").iterdir())
    pkg_name = pkg_dir.name
    src_target = ROOT / "src" / pkg_name
    tests_target = ROOT / "tests" / pkg_name
    if src_target.exists() or tests_target.exists():
        sys.exit(f"ERROR: package '{pkg_name}' already exists in src/ or tests/")
    (ROOT / "src").mkdir(exist_ok=True)
    (ROOT / "tests").mkdir(exist_ok=True)
    shutil.move(str(holder / "src" / pkg_name), str(src_target))
    shutil.move(str(holder / "tests" / pkg_name), str(tests_target))
    shutil.rmtree(holder.parent)
    return pkg_name


def main() -> None:
    pkg = relocate(render_to_tempdir(sys.argv[1:]))
    print(f"\nCreated package '{pkg}':")
    print(f"  src/{pkg}/")
    print(f"  tests/{pkg}/")
    print(f"Package auto-discovered by setuptools. Run `uv sync` to refresh.")


if __name__ == "__main__":
    main()
