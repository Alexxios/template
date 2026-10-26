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

The helper copies `src/base/` into `src/python-lib/` without rendering the
Cookiecutter variables. The new template includes the base tooling, hooks,
dependency manifest, and nested package generator. Existing directories are
never overwritten.

Customize `src/python-lib/cookiecutter.json`, the files in
`src/python-lib/{{cookiecutter.project_slug}}/`, and its hooks. The dependency
manifest is at `src/python-lib/templates/dependencies/pyproject.toml`.
Each template is an independent copy; later edits to `base` do not propagate.

To start from another template in the collection:

```bash
uv run python scripts/new_template.py cli-tool --from python-lib
```

Generate a project locally, then commit and push the new template to make it
available from the remote repository:

```bash
cookiecutter . --directory src/python-lib
cookiecutter gh:Alexxios/template --directory src/python-lib
```

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
exercise its nested package helper. Add template-specific tests when a new
template's structure or inputs diverge from the starter.

Outer CI continues to generate the base project, create a temporary repository,
wait for that repository's own CI, retrieve its reports, and delete it. The
repository's own tests, lint, and documentation checks run separately.
