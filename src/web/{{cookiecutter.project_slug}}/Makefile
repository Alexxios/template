UV ?= uv
PYTHON ?= $(UV) run --all-packages python
export NAME DESCRIPTION

.DEFAULT_GOAL := help
.PHONY: help bootstrap new-service new-lib test lint format docs serve codegen check-generated check

help:
	@printf '%s\n' \
	  'bootstrap  Install development and documentation tools' \
	  'new-service  Create a service (NAME=api, optional DESCRIPTION=...)' \
	  'new-lib    Create a library (NAME=common, optional DESCRIPTION=...)' \
	  'test       Run pytest with coverage' \
	  'lint       Check code and formatting' \
	  'format     Format Python files' \
	  'docs       Build documentation' \
	  'serve      Serve documentation locally' \
	  'codegen    Render the workspace README from its Jinja templates' \
	  'check-generated  Check generated files without writing' \
	  'check      Run lint, tests, and documentation checks'

bootstrap:
	@test -f .env || cp .env.example .env
	$(UV) sync --all-packages --extra dev --extra docs

new-service new-lib:
	@test -n "$$NAME" || { printf 'Usage: make %s NAME=package_name [DESCRIPTION="..."]\n' '$@' >&2; exit 1; }
	$(PYTHON) scripts/new_workspace_member.py $(patsubst new-%,%,$@) "$$NAME" --description "$$DESCRIPTION"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format:
	$(UV) run --all-packages ruff format .

docs:
	$(UV) run --all-packages mkdocs build --strict

serve:
	$(UV) run --all-packages mkdocs serve

codegen:
	$(PYTHON) scripts/codegen.py

check-generated:
	$(PYTHON) scripts/codegen.py --check

check: check-generated lint test docs
