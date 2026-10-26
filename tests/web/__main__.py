"""Render or scaffold this template's CI fixture."""

from pathlib import Path

from tests.support import main

from .scaffold import scaffold

if __name__ == "__main__":
    main(Path(__file__).parent, scaffold)
