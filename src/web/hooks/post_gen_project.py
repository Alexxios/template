"""Keep the selected CI configurations."""

import shutil
from pathlib import Path

ROOT = Path.cwd()

if "{{cookiecutter.ci_github}}" != "yes":
    shutil.rmtree(ROOT / ".github")
if "{{cookiecutter.ci_sourcecraft}}" != "yes":
    shutil.rmtree(ROOT / ".sourcecraft")
