# Usage

## Installation

```bash
poetry install
```

## Development workflow

```bash
# install all groups
poetry install --with dev,docs

# enable pre-commit
poetry run pre-commit install

# run tests with coverage
poetry run pytest

# run the full matrix
poetry run tox

# serve docs locally
poetry run mkdocs serve
```
