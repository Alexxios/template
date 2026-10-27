"""Keep the selected CI configurations and render the initial workspace README."""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

if "{{cookiecutter.ci_github}}" != "yes":
    shutil.rmtree(ROOT / ".github")
if "{{cookiecutter.ci_sourcecraft}}" != "yes":
    shutil.rmtree(ROOT / ".sourcecraft")

subprocess.run([sys.executable, str(ROOT / "scripts/codegen.py")], cwd=ROOT, check=True)
