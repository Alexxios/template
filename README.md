# Python Project Template

A [Cookiecutter](https://www.cookiecutter.io/) template for modern Python projects, pre-wired with:

- **Poetry** for dependency management and packaging
- **black** + **isort** for formatting
- **flake8** for linting (black-compatible)
- **pytest** + **coverage.py** (via `pytest-cov`) for tests
- **tox** for multi-Python-version test matrix
- **pre-commit** hooks for the formatters/linters
- **MkDocs** + **Material** theme for Markdown-based docs
- `src/`-layout package skeleton with a smoke test

## Usage

Install cookiecutter (one-time):

```bash
pipx install cookiecutter
```

Generate a project from this template:

```bash
# from a local checkout
cookiecutter /path/to/this/template

# or from GitHub
cookiecutter gh:<your-user>/<this-repo>
```

You will be prompted for:

| Variable             | Purpose                                                              |
| -------------------- | -------------------------------------------------------------------- |
| `project_name`       | Human-readable name                                                  |
| `project_slug`       | Directory name (auto from `project_name`, override if needed)        |
| `package_name`       | Importable Python package name (auto from slug)                      |
| `description`        | Short project description                                            |
| `author_name`        | Author name for `pyproject.toml`                                     |
| `author_email`       | Author email for `pyproject.toml`                                    |
| `version`            | Initial version                                                      |
| `python_version`     | Primary Python version used for dev                                  |
| `python_min_version` | Lower bound; floor of the tox matrix and Poetry `python` constraint  |
| `license`            | One of MIT, Apache-2.0, BSD-3-Clause, Proprietary                    |
| `init_git`           | If `yes`, run `git init` and create an initial commit                |
| `ci_sourcecraft`     | If `yes`, generate `.sourcecraft/ci.yaml` with test/lint/docs flows  |
| `ci_github`          | If `yes`, generate `.github/workflows/ci.yml` with test/lint/docs    |
| `ci_gitlab`          | If `yes`, generate `.gitlab-ci.yml` with test/lint/docs jobs         |

## After generation

```bash
cd <project_slug>
poetry install --with dev,docs
poetry run pre-commit install
poetry run pytest
poetry run tox
poetry run mkdocs serve
```

## What's not included

Release automation, Docker, and type-checkers (mypy/ruff) are intentionally
out of scope — add them per project. CI is opt-in via the `ci_sourcecraft`,
`ci_github`, and `ci_gitlab` flags; each enabled flag scaffolds parallel
`test` / `lint` / `docs` flows for that provider.
