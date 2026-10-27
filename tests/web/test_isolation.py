"""Exercise real uv environments to catch undeclared sibling dependencies."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .test_web import JUST, generate
from .test_web import project as project


def test_member_environment_requires_declared_workspace_dependencies(project):
    for name in ("consumer", "provider", "unrelated"):
        assert generate(project, "lib", name).returncode == 0
    test = project / "libs/consumer/tests/test_smoke.py"
    test.write_text(
        "import importlib.util\n\nimport provider\n\n\n"
        "def test_dependencies():\n"
        "    assert provider is not None\n"
        '    assert importlib.util.find_spec("unrelated") is None\n'
    )
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    uv = Path(sys.prefix) / "bin/uv"
    env["UV"] = str(uv if uv.exists() else shutil.which("uv"))
    command = [JUST, "test", "libs/consumer"]
    broken = subprocess.run(
        command, cwd=project, env=env, capture_output=True, text=True, timeout=120
    )
    assert broken.returncode != 0
    assert "No module named 'provider'" in broken.stdout, broken.stdout + broken.stderr
    manifest = project / "libs/consumer/pyproject.toml"
    manifest.write_text(
        manifest.read_text().replace("dependencies = []", 'dependencies = ["provider"]')
        + "\n[tool.uv.sources]\nprovider = { workspace = true }\n"
    )
    fixed = subprocess.run(
        command, cwd=project, env=env, capture_output=True, text=True, timeout=120
    )
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    assert "1 passed" in fixed.stdout
    assert (project / ".venvs/libs/consumer/pyvenv.cfg").is_file()
    assert not (project / ".venvs/libs/provider").exists()
