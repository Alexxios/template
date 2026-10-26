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
	@test -f .env || cp .env.example .env
	$(UV) sync --all-packages --extra dev --extra docs

test:
	$(UV) run --all-packages python -m pytest

lint:
	$(UV) run --all-packages ruff check .
	$(UV) run --all-packages ruff format --check .

format:
	$(UV) run --all-packages ruff format .

docs:
	$(UV) run --all-packages mkdocs build --strict

serve:
	$(UV) run --all-packages mkdocs serve

check: lint test docs
