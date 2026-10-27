"""Render the initial workspace README."""

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

subprocess.run([sys.executable, str(ROOT / "scripts/codegen.py")], cwd=ROOT, check=True)
