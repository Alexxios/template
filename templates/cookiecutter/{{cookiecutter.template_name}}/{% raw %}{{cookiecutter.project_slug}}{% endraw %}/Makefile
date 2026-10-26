UV ?= uv

.DEFAULT_GOAL := help
.PHONY: help bootstrap test lint format docs serve check

help:
	@printf '%s\n' \
	  'bootstrap  Install development and documentation tools' \
	  'test       Run pytest with coverage' \
	  'lint       Check code and formatting' \
	  'format     Format Python files' \
	  'docs       Build documentation' \
	  'serve      Serve documentation locally' \
	  'check      Run lint, tests, and documentation checks'

bootstrap:
	$(UV) sync --extra dev --extra docs

test:
	$(UV) run python -m pytest

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff format .

docs:
	$(UV) run mkdocs build --strict

serve:
	$(UV) run mkdocs serve

check: lint test docs
