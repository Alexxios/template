UV ?= uv
export NAME

.DEFAULT_GOAL := help
.PHONY: help bootstrap new-template sync-templates check-generated test lint format docs serve tox check

help:
	@printf '%s\n' \
	  'bootstrap          Install development and documentation tools' \
	  'new-template       Create a template, fixture, and CI workflow (NAME=python-lib)' \
	  'sync-templates     Regenerate validation workflows and README badges' \
	  'check-generated    Check generated files without changing them' \
	  'test               Run repository tests with coverage' \
	  'lint               Check code and formatting' \
	  'format             Format repository Python files' \
	  'docs               Build documentation' \
	  'serve              Serve documentation locally' \
	  'tox                Run the tox environments' \
	  'check              Check generated files, lint, tests, and documentation'

bootstrap:
	$(UV) sync --extra dev --extra docs

new-template:
	@test -n "$$NAME" || { printf '%s\n' 'Usage: make new-template NAME=python-lib' >&2; exit 1; }
	$(UV) run python scripts/new_template.py "$$NAME"

sync-templates:
	$(UV) run python scripts/sync_templates.py

check-generated:
	$(UV) run python scripts/sync_templates.py --check

test:
	$(UV) run python -m pytest

lint:
	$(UV) run ruff check scripts tests
	$(UV) run ruff format --check scripts tests

format:
	$(UV) run ruff format scripts tests

docs:
	$(UV) run mkdocs build --strict

serve:
	$(UV) run mkdocs serve

tox:
	$(UV) run tox

check: check-generated lint test docs
