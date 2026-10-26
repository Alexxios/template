# Python Template Collection

[![CI](https://github.com/Alexxios/template/actions/workflows/ci.yml/badge.svg)](https://github.com/Alexxios/template/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/dynamic/xml?url=https%3A%2F%2Falexxios.github.io%2Ftemplate%2Fjunit.xml&query=%2Ftestsuites%2Ftestsuite%2F%40tests&label=tests&color=blue)](https://alexxios.github.io/template/)
[![Coverage](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Falexxios.github.io%2Ftemplate%2Fcoverage.json&query=%24.totals.percent_covered_display&label=coverage&suffix=%25&color=blue)](https://alexxios.github.io/template/coverage/)

A collection of [Cookiecutter](https://www.cookiecutter.io/) templates under `src/`.
The repository also acts as a metatemplate: `scripts/new_template.py` creates a
new selectable template from an existing starter.

```text
src/
└── base/
    ├── cookiecutter.json
    ├── hooks/
    ├── templates/dependencies/pyproject.toml
    └── {{cookiecutter.project_slug}}/
scripts/
├── new_template.py
└── sourcecraft_repo.py
tests/
docs/
pyproject.toml
tox.ini
.pre-commit-config.yaml
mkdocs.yml
LICENSE
```

The `base` template retains the existing Python project tooling:

- **uv** for dependency management and packaging
- **mashumaro** + **orjson** for serialization
- **structlog** for structured logging
- **dishka** for dependency injection
- **pytest-profiling** for CPU profiles and SVG call graphs
- **pytest-memray** + **memray** for memory profiling (Linux/macOS)
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
cookiecutter /path/to/this/template --directory src/base

# or from GitHub
cookiecutter gh:Alexxios/template --directory src/base
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

## Create a new template

```bash
uv sync --extra dev --extra docs
uv run python scripts/new_template.py python-lib
cookiecutter . --directory src/python-lib
```

This copies `src/base/` into `src/python-lib/`, including its hooks, dependency
manifest, nested package helper, and project tooling. Cookiecutter expressions
stay unrendered, and existing templates are never overwritten. Customize the new
template's `cookiecutter.json` and `{{cookiecutter.project_slug}}/` directory.
Use `--from another-template` to copy a different starter.

After committing and pushing the new template, projects can use it directly:

```bash
cookiecutter gh:Alexxios/template --directory src/python-lib
```

Templates are independent copies: edits to `base` do not propagate to existing
templates. Choose the template through `--directory`; the former unused
`designation` prompt has been removed.

## Develop this repository

The repository follows the base layout with `src/`, `tests/`, `scripts/`, and
`docs/`, plus its own uv, pytest, Ruff, pre-commit, tox, and MkDocs configuration.
It requires Python 3.14. It is a tooling project, so uv does not install `src/`
as a Python package. Repository and CI dependencies are declared in `pyproject.toml`.

```bash
uv sync --extra dev --extra docs
uv run pre-commit install
uv run pytest
uv run tox
uv run mkdocs serve
```

Root checks validate the scaffolding helper and render every template under
`src/`. Raw template payloads are excluded from repository linting; generated
projects retain their own checks. The existing Sourcecraft API helper is kept
unchanged and is outside the new Ruff checks.

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
`ci_github`, and `ci_gitlab` flags. All three provide test, lint, and docs checks.
GitHub also publishes test reports with coverage and profiling.

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

## GitHub CI and reports

The outer workflow runs on pushes to `main`/`master`, pull requests, and manual
dispatches. A separate job checks this repository's tests, lint, and docs.
The integration job validates the base project's own GitHub CI end to end:

1. Generate a Python 3.14 project with `--directory src/base` and scaffold three additional packages.
2. Create a temporary GitHub repository and push the generated project.
3. Trigger and wait for its own workflow, matching the workflow, event, branch,
   and generated commit. A failed inner workflow fails the outer workflow.
4. Download its logs and reports as the outer run's `generated-ci` artifact,
   then delete the temporary repository, including after failures.

For an outer pull request, CI opens a pull request in the temporary project.
That project's `pull-request.yml` runs tests with coverage, Ruff lint/formatting,
and the docs PDF build. It does not run profiling or publish to Pages.

For an outer push or manual run, CI configures Pages in the temporary repository
and pushes to its `main` branch. The project's `ci.yml` runs tests with coverage,
CPU and memory profiling, builds Allure, and deploys its reports. On the outer
`main`/`master` branches, the downloaded reports are also published to this
repository's Pages site before the next run replaces them. Failed tests retain
their reports and leave the outer run failed.

### Integration credentials

Keep the repository secret `CI_GITHUB_TOKEN`: use a classic PAT with `repo`,
`workflow`, and `delete_repo` scopes. It must be able to create, push to, configure
Pages in, and delete repositories under the selected owner. The optional
`CI_GITHUB_OWNER` repository variable selects a different owner; otherwise the
mirror's owner is used. Temporary repositories match this repository's public
or private visibility. Private repositories need a GitHub plan that supports
[Pages for private repositories](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

The integration check fails explicitly when the token is unavailable, including
fork PRs. For Dependabot PRs, configure `CI_GITHUB_TOKEN` as a Dependabot secret
as well. Generated projects themselves use only their built-in `GITHUB_TOKEN`.

### Enable Pages

1. In [Settings → Pages](https://github.com/Alexxios/template/settings/pages), set
   **Build and deployment → Source → GitHub Actions**.
2. If the `github-pages` environment restricts deployment branches, allow both
   `main` and `master`.
3. Configure `CI_GITHUB_TOKEN` above and push to `main` or `master`. The outer
   workflow publishes the reports downloaded from the generated project's CI.

The [Pages site](https://alexxios.github.io/template/) opens the native Allure report.
Other outputs are served directly:

| Path | Report |
| --- | --- |
| `/` | Allure test results and history |
| `/coverage/` | HTML line and branch coverage |
| `/profiling/combined.svg` | CPU call graph |
| `/profiling/*.prof` | Per-test and combined CPU profiles |
| `/memory/*.html`, `/memory/*.bin` | Per-test memory flame graphs and captures |
| `/junit.xml`, `/coverage.xml`, `/coverage.json`, `/pytest.txt` | Raw reports and pytest output |
| `/history.jsonl` | Allure 3 history |

The README badges use Shields.io's dynamic XML/JSON APIs to read JUnit and
coverage reports directly. The tests badge shows the test count; the coverage
badge shows coverage.py's combined line/branch percentage.

Each deployment replaces the site with reports from a generated project's run.
Publishing is serialized. The outer report measures generated project code;
each temporary repository starts with fresh history. In permanent generated
projects, Allure history is restored from a branch-specific Actions cache and
saved after report generation, including failed tests. Cache eviction starts a
new history.

Reports are publicly served by Pages, including coverage source listings.
Coverage and both profilers run together, so timings include instrumentation
overhead. pytest-profiling names files after test names; generated smoke tests
have package-specific names to avoid collisions. Give custom tests unique names
within a profiling run.

## Dependency updates

Dependabot checks weekly and opens grouped update pull requests on GitHub.
The template repository's `.github/dependabot.yml` covers its own Actions and
repository and CI tools (`pyproject.toml`, using uv),
plus each template's
Actions, Python dependencies (`src/*/templates/dependencies/pyproject.toml`, also using uv),
Allure CLI (`src/*/{{cookiecutter.project_slug}}/.github/package.json`, using npm), and
pre-commit hooks. The workflow directory rules cover both generated workflows,
including `pull-request.yml`.

Projects generated with `ci_github=yes` also include `.github/dependabot.yml`.
They receive weekly updates for GitHub Actions, Python dependencies through uv
(including `uv.lock` when committed), Allure CLI through npm, and pre-commit hooks.
The reporting workflow installs the Allure version declared in `.github/package.json`.
Python updates use `versioning-strategy: increase` so lower bounds such as `ruff>=0.7.0` are updated
even when the newest release already satisfies the existing range.

Each template's Python dependency manifest is valid TOML that Dependabot can update.
Cookiecutter imports its dependency sections into each generated `pyproject.toml`.
This updates the template's runtime, development, documentation, and build dependencies
from the outer repository. Generated projects contain ordinary dependency lists
and update them independently. Their `python_min_version` setting is rendered
directly as before.

GitHub-expression strings in workflow templates are quoted so Dependabot can
parse the YAML before Cookiecutter renders it.

Merge these configurations into each GitHub repository's default branch to
activate updates. Merge dependency PRs on GitHub, then fetch those changes and
push them to Sourcecraft when updating the primary repository.
