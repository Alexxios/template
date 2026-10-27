"""Add a small application to a generated workspace for inner CI to validate."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def scaffold(project: Path) -> None:
    for kind, name in (
        ("service", "api"),
        ("service", "worker"),
        ("lib", "shared_utils"),
        ("lib", "storage"),
    ):
        subprocess.run(
            [str(Path(sys.prefix) / "bin/just"), f"new-{kind}", name],
            cwd=project,
            env={**os.environ, "PYTHON": shlex.quote(sys.executable)},
            check=True,
        )

    for group, name, dependency in (
        ("services", "api", "shared_utils"),
        ("services", "worker", "storage"),
        ("libs", "storage", "shared_utils"),
    ):
        manifest = project / group / name / "pyproject.toml"
        distribution = dependency.replace("_", "-")
        content = manifest.read_text().replace(
            "dependencies = []", f'dependencies = ["{distribution}"]'
        )
        manifest.write_text(
            content + f"\n[tool.uv.sources]\n{distribution} = {{ workspace = true }}\n"
        )

    (project / "libs/shared_utils/src/shared_utils/message.py").write_text(
        'def message() -> str:\n    return "workspace ready"\n'
    )
    (project / "libs/storage/src/storage/status.py").write_text(
        "from shared_utils.message import message\n\n\ndef status() -> str:\n    return message()\n"
    )
    for name, imported, function in (
        ("api", "shared_utils.message", "message"),
        ("worker", "storage.status", "status"),
    ):
        (project / f"services/{name}/src/{name}/main.py").write_text(
            f"from {imported} import {function}\n\n\ndef main() -> str:\n    return {function}()\n"
        )
    (project / "tests/test_workspace.py").write_text(
        "from api.main import main as api_main\n"
        "from worker.main import main as worker_main\n\n\n"
        "def test_workspace_dependencies():\n"
        '    assert api_main() == worker_main() == "workspace ready"\n'
    )
