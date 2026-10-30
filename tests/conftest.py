"""Keep Cookiecutter caches and replay files inside each test directory."""

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def collection(tmp_path, cookiecutter_config):
    root = tmp_path / "collection"
    shutil.copytree(ROOT / "templates", root / "templates")
    workflows = root / ".github/workflows"
    workflows.mkdir(parents=True)
    for filename in ("pages.yml", "template-validation.yml"):
        shutil.copy2(ROOT / ".github/workflows" / filename, workflows / filename)
    (root / "scripts").mkdir()
    for filename in ("__init__.py", "new_template.py", "sync_templates.py"):
        shutil.copy2(ROOT / "scripts" / filename, root / "scripts" / filename)
    (root / "tests").mkdir()
    for filename in ("__init__.py", "support.py"):
        shutil.copy2(ROOT / "tests" / filename, root / "tests" / filename)
    (root / "README.md").write_text("# Test collection\n\nHand-written documentation.\n")
    shutil.copy2(ROOT / "pyproject.toml", root / "pyproject.toml")
    return root


@pytest.fixture
def cookiecutter_config(tmp_path, monkeypatch):
    config = tmp_path / "cookiecutter-config.json"
    config.write_text(
        json.dumps(
            {
                "cookiecutters_dir": str(tmp_path / "cookiecutters"),
                "replay_dir": str(tmp_path / "replay"),
            }
        )
    )
    monkeypatch.setenv("COOKIECUTTER_CONFIG", str(config))
    return config
