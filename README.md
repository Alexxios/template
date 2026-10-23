# Python Project Template

A [Cookiecutter](https://www.cookiecutter.io/) template for modern Python projects, pre-wired with:

- **uv** for dependency management and packaging
- **Ruff** for both formatting and linting (replaces black/isort/flake8)
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
cookiecutter gh:Alexxios/template
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
| `python_min_version` | Lower bound; floor of the tox matrix and `requires-python` constraint |
| `license`            | One of MIT, Apache-2.0, BSD-3-Clause, Proprietary                    |
| `init_git`           | If `yes`, run `git init` and create an initial commit                |
| `ci_sourcecraft`     | If `yes`, generate `.sourcecraft/ci.yaml` with test/lint/docs flows  |
| `ci_github`          | If `yes`, generate GitHub CI and Dependabot configuration           |
| `ci_gitlab`          | If `yes`, generate `.gitlab-ci.yml` with test/lint/docs jobs         |

## After generation

```bash
cd <project_slug>
uv sync --extra dev --extra docs
uv run pre-commit install
uv run pytest
uv run tox
uv run mkdocs serve
```

## What's not included

Release automation, Docker, and type-checkers (mypy/pyright) are intentionally
out of scope — add them per project. CI is opt-in via the `ci_sourcecraft`,
`ci_github`, and `ci_gitlab` flags; each enabled flag scaffolds parallel
`test` / `lint` / `docs` flows for that provider.

## GitHub mirror

The primary repository is on Sourcecraft. The GitHub mirror is
[Alexxios/template](https://github.com/Alexxios/template).
For an existing Sourcecraft checkout, add the second remote once:

```bash
git remote add github https://github.com/Alexxios/template.git
```

Push branches and tags to GitHub when updating the mirror:

```bash
git push github --all
git push github --tags
```

## GitHub CI

The template's `.github/workflows/ci.yml` runs on pushes to `main`/`master`,
pull requests, and manual dispatches. Like Sourcecraft CI, it generates a
Python 3.14 project, scaffolds three additional packages, and validates the
result. It enables only the generated project's GitHub workflow.

For the full create/push/wait/download/delete cycle, configure the repository
secret `CI_GITHUB_TOKEN` with a classic personal access token with `repo`,
`workflow`, and `delete_repo` scopes. The token must be able to create and delete
private repositories under the mirror's owner. Set the optional repository
variable `CI_GITHUB_OWNER` to use a different owner. A separate token is needed
because the built-in `GITHUB_TOKEN` cannot create repositories, and pushes made
with it do not trigger the generated project's CI.

When the secret is unavailable (including fork pull requests), CI runs the
generated project's pytest, Ruff, documentation, and report commands locally.
Both modes publish `allure-report` (the full report directory, including
`index.html` and JSON summaries) and `docs-pdf` (`docs.pdf`)
artifacts. The generated GitHub workflow also publishes these reports and runs
its test, lint, and docs jobs in parallel.

Both workflows use the [official Allure action](https://allurereport.org/docs/integrations-github-action/)
to post test summaries on pull requests from the same repository, including
when tests fail. This uses the built-in `GITHUB_TOKEN`; the reporting jobs
request `pull-requests: write` and `checks: write` permissions. Fork and
Dependabot pull requests retain report artifacts without posting comments.
The full report directory is preserved when transferring reports from temporary
repositories so the action can read Allure's JSON summaries.

## Dependency updates

Dependabot checks weekly and opens grouped update pull requests on GitHub.
The template repository's `.github/dependabot.yml` covers its own Actions and
CI tools (`requirements-ci.txt`, using the uv ecosystem), plus the template's
Actions, Python tooling (`templates/dependencies/pyproject.toml`, also using uv),
and pre-commit hooks.

Projects generated with `ci_github=yes` also include `.github/dependabot.yml`.
They receive weekly updates for GitHub Actions, Python dependencies through uv
(including `uv.lock` when committed), and pre-commit hooks. Python updates use
`versioning-strategy: increase` so lower bounds such as `ruff>=0.7.0` are updated
even when the newest release already satisfies the existing range.

The shared Python tooling manifest is valid TOML that Dependabot can update.
Cookiecutter imports its dependency sections into each generated `pyproject.toml`.
This updates the template's development, documentation, and build dependencies
from the outer repository. Generated projects contain ordinary dependency lists
and update them independently. Their `python_min_version` setting is rendered
directly as before.

GitHub-expression strings in workflow templates are quoted so Dependabot can
parse the YAML before Cookiecutter renders it.

Merge these configurations into each GitHub repository's default branch to
activate updates. Merge dependency PRs on GitHub, then fetch those changes and
push them to Sourcecraft when updating the primary repository.
