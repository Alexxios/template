"""Scaffold a new package under src/ and tests/.

Wraps the inner cookiecutter at ``templates/package/``: generates into a temp
dir, moves the rendered ``src/<pkg>`` and ``tests/<pkg>`` into the project,
and appends the package to the ``packages`` array in ``pyproject.toml``.

Usage:
    poetry run python scripts/new_package.py
    poetry run python scripts/new_package.py --no-input package_name=my_pkg
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "package"
PYPROJECT = ROOT / "pyproject.toml"


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


def register_in_pyproject(pkg_name: str) -> None:
    text = PYPROJECT.read_text()
    new_entry = f'    {{ include = "{pkg_name}", from = "src" }},'
    if re.search(rf'include\s*=\s*"{re.escape(pkg_name)}"', text):
        print(f"NOTE: '{pkg_name}' already listed in pyproject.toml packages")
        return
    pattern = re.compile(r"(packages\s*=\s*\[)([^\]]*)(\])", re.DOTALL)
    match = pattern.search(text)
    if not match:
        print(
            f"WARN: could not find `packages = [...]` block in pyproject.toml. "
            f"Add manually: {new_entry.strip()}",
            file=sys.stderr,
        )
        return
    body = match.group(2).rstrip()
    if body and not body.endswith(","):
        body += ","
    new_block = f"{match.group(1)}{body}\n{new_entry}\n{match.group(3)}"
    PYPROJECT.write_text(text[: match.start()] + new_block + text[match.end() :])


def main() -> None:
    pkg = relocate(render_to_tempdir(sys.argv[1:]))
    register_in_pyproject(pkg)
    print(f"\nCreated package '{pkg}':")
    print(f"  src/{pkg}/")
    print(f"  tests/{pkg}/")
    print("Registered in pyproject.toml. Run `poetry install` to pick it up.")


if __name__ == "__main__":
    main()
