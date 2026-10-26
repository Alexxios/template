# Usage

## Generate a project

```bash
cookiecutter gh:Alexxios/template --directory src/base
# Or an empty service/library workspace:
cookiecutter gh:Alexxios/template --directory src/web
# From a local checkout:
cookiecutter . --directory src/base
```

## Web workspace

The `web` template starts with empty `services/`, `libs/`, and `tests/` directories.
It provides per-member package generators and an empty infrastructure starter.
It retains the Makefile, LICENSE, pre-commit, MkDocs, and Python tooling.

```bash
cd <project_slug>
make bootstrap
uv run python scripts/new_service.py api
uv run python scripts/new_lib.py common
uv add --package api ./libs/common
make bootstrap
make check
```

Choose your own member names and application framework. A service owns its
`src/<name>/`, tests, `pyproject.toml`, and Dockerfile. A library has the same Python
layout without a container. Service entry points are placeholders to implement.
The root `tests/` is for integration tests across members. Helpers refuse duplicate
names and work from any current directory. `templates/member/` is customizable.

`make bootstrap` installs all members and copies `.env.example` to `.env` if absent.
Commit `uv.lock`. Add dependencies with `uv add --package <name> <dependency>`;
use a local library path to declare a workspace dependency. Build containers from
the workspace root after configuring services in `infra/docker-compose.yml`.
The generated infrastructure README contains an example.

GitHub CI defaults to enabled. `pull-request.yml` handles PR checks and retains
`check-reports`. `ci.yml` checks the repository's default branch and also uploads
`github-pages`, containing the documentation site and test reports under
`reports/`. It follows the default branch in the repository settings and uploads
the Pages artifact without deploying a site. Select `ci_sourcecraft=yes` for
Sourcecraft, which runs `make check` and retains JUnit and coverage reports.

## Create a template

```bash
make bootstrap
make new-template NAME=python-lib
```

This renders the tooling-only seed from `templates/cookiecutter/` into
`src/python-lib/`, generates `tests/python_lib/` and its validation workflow, adds
a Sourcecraft validation workflow, and refreshes the root README status table.
Existing fixture packages are preserved. Hyphens in template names become
underscores in their Python test-package names.

Customize the project payload and `cookiecutter.json` as before. In the test
package, edit `scaffold.py` to define `scaffold(project: Path)`, adding example code
and tests for the generated project's inner CI. Edit `validation.toml` to configure
Cookiecutter context, inner workflow names, artifact names, and Sourcecraft cubes.
Use `push_artifact_format = "pages"` for a Pages archive or `"directory"` for
ordinary reports. `publish_pages` controls Pages setup and outer deployment
separately; web collects its Pages archive with deployment disabled.
The generated `__main__.py` delegates to the common CLI in `tests/support.py`:

```bash
uv run python -m tests.python_lib render /tmp/python-lib-fixture --ci github
uv run python -m tests.python_lib scaffold /tmp/python-lib-fixture
```

Select `--ci sourcecraft` to generate a Sourcecraft fixture. The default scaffold
adds a small tested example to the integration fixture only; the project seed
continues to contain no application layout.

Workflows and the README status table are generated from `templates/validation/`:

```bash
make sync-templates
make check-generated
```

Run sync after editing workflow sources or `validation.toml`, or after adding a
template directly under `src/`. For direct Cookiecutter creation:

```bash
uv run cookiecutter templates/cookiecutter --output-dir src template_name=python-lib
make sync-templates
```

Commit all generated files along with the template. CI checks that they are up
to date. The README's marked status section is generated; its remaining text is
preserved. Set `tool.template_ci.repository` in the root `pyproject.toml` to control
badge URLs when forking this collection.

Each template is an independent snapshot of the project tooling seed. Later seed
changes do not rewrite templates. Later syncs preserve custom fixture packages
and rebuild their workflow definitions. Generate projects with:

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
make bootstrap
uv run pre-commit install
make check
make serve
```

Use `make help` for all targets. Individual checks are available through
`make check-generated`, `make lint`, `make test`, and `make docs`; `make format`
formats repository Python files and `make tox` runs the tox environments.
The repository CI uses the same Make targets.

Generation tests render every template under `src/`. The base checks also
exercise its nested package helper. Metatemplate checks render both the new
template and its resulting project. Add template-specific tests when a new
template's structure or inputs diverge from the starter.

Each template has an independent GitHub validation workflow and a Sourcecraft
workflow. They render and scaffold via the template's test package, create a
temporary repository, wait for its configured inner CI, collect results, and
delete the repository. Results are retained as `generated-<template>-ci` on GitHub.
An inner failure fails its outer workflow. Repository tests, lint, documentation,
and generated-file checks run separately in `ci.yml`.

GitHub is the primary repository for development and pull requests. Sourcecraft
CI configuration and its integration workflow are retained; any Sourcecraft
mirror should follow GitHub.
