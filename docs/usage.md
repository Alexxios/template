# Usage

## Generate a project

```bash
cookiecutter gh:Alexxios/template --directory src/base
# From a local checkout:
cookiecutter . --directory src/base
```

## Create a template

Install the repository tooling, then scaffold a new template:

```bash
uv sync --extra dev --extra docs
uv run python scripts/new_template.py python-lib
```

The helper runs the Cookiecutter metatemplate at `templates/cookiecutter/`.
It creates `src/python-lib/cookiecutter.json` and a project payload with a
Makefile, LICENSE, pyproject, README, gitignore, pre-commit, MkDocs, and optional
CI configuration. Existing templates are never overwritten.

It adds no application source, tests, services, libraries, or package generators.
Ruff, pytest, and coverage discover files without assuming a source layout.
Packaging starts disabled. The included `docs/` is a MkDocs starter page.

Customize `src/python-lib/cookiecutter.json`, the files in
`src/python-lib/{{cookiecutter.project_slug}}/`, and its hooks. The dependency
manifest is at `src/python-lib/templates/dependencies/pyproject.toml`.
Each template is an independent snapshot of the seed. Later seed edits do not
rewrite existing templates.

Alternatively, use Cookiecutter directly instead of the helper:

```bash
uv run cookiecutter templates/cookiecutter --output-dir src template_name=python-lib
```

Generate a project locally, then commit and push the new template to make it
available from the remote repository:

```bash
cookiecutter . --directory src/python-lib
cookiecutter gh:Alexxios/template --directory src/python-lib
```

## Generated tooling

Use `make bootstrap` to install development and documentation dependencies.
The Makefile also offers `lint`, `format`, `test`, `docs`, `serve`, and `check`.
Add application code and tests before running `make check`; pytest reports an
error if there are no tests. Enable packaging and select a build backend when
your chosen layout needs an installable package.

GitHub CI is enabled by default. Sourcecraft remains available by setting
`ci_sourcecraft=yes` during project generation. The basic CI configurations run
the same Make targets.

## Repository development

Use Python 3.14. Install repository and CI tooling from `pyproject.toml`:

```bash
uv sync --extra dev --extra docs
uv run pre-commit install
uv run pytest
uv run tox
uv run mkdocs serve
```

Generation tests render every template under `src/`. The base checks also
exercise its nested package helper. Metatemplate checks render both the new
template and its resulting project. Add template-specific tests when a new
template's structure or inputs diverge from the starter.

Outer CI continues to generate the base project, create a temporary repository,
wait for that repository's own CI, retrieve its reports, and delete it. The
repository's own tests, lint, and documentation checks run separately.

GitHub is the primary repository for development and pull requests. Sourcecraft
CI configuration and its integration workflow are retained; any Sourcecraft
mirror should follow GitHub.
