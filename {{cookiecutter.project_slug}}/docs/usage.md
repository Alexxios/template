# Usage

## Installation

```bash
uv sync
```

## Development workflow

```bash
# install all extras
uv sync --extra dev --extra docs

# enable pre-commit
uv run pre-commit install

# run tests with coverage
uv run pytest

# run the full matrix
uv run tox

# serve docs locally
uv run mkdocs serve
```
