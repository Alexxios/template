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
make new-service NAME=api
make new-lib NAME=common
uv add --package api ./libs/common
make bootstrap
make check
```

Choose your own member names and application framework. A service owns its
`src/<name>/`, tests, `pyproject.toml`, and Dockerfile. A library has the same Python
layout without a container. Service entry points are placeholders to implement.
The root `tests/` is for integration tests across members. Creation commands
refuse duplicate names. Pass `DESCRIPTION="..."` for a custom description.
Use `make -C /path/to/workspace new-service NAME=api` from another directory.
Customize `templates/service/` and
`templates/lib/` independently; libraries never include service-only files.

Member READMEs get direct Shields links for lint (including formatting), their
own tests, and line/branch coverage during scaffolding. They remain editable and
are never rewritten by codegen. The entire workspace README is generated from
`templates/readme/README.md.jinja`, which includes `header.md.jinja` for the sorted
service/library tables and badges. Edit those Jinja templates to customize the
workspace documentation. Creating a member runs codegen automatically; run
`make codegen` after manual additions, removals, renames, template edits, or changes
to `tool.codegen.reports_url`. `make check-generated` detects stale output without
writing files. Update existing member README links directly after changing hosts.

The root `pyproject.toml` remains editable. Pytest searches `tests`,
`services/*/tests`, and `libs/*/tests`; it picks up new members automatically and
does not collect source modules that happen to match test naming conventions.
Workspace membership and Ruff source paths also use globs, so adding a member
does not require regenerating this file or rewriting dependencies.

`make bootstrap` installs all members and copies `.env.example` to `.env` if absent.
Commit `uv.lock`. Add dependencies with `uv add --package <name> <dependency>`;
use a local library path to declare a workspace dependency. Build containers from
the workspace root after configuring services in `infra/docker-compose.yml`.
The generated infrastructure README contains an example.

GitHub CI defaults to enabled. `pull-request.yml` handles PR checks and retains
`check-reports`. `ci.yml` checks the repository's default branch and also uploads
`github-pages`, containing the documentation site and test reports under
`reports/`. It follows the default branch in the repository settings and uploads
the Pages artifact before automatically deploying it. Set `github_repository` to
`owner/repo` during generation, then select **GitHub Actions** as the repository's
Pages source once. Set `reports_url` during generation or
`tool.codegen.reports_url` afterward for a custom public host.
`make lint` runs Ruff and its formatting check directly; `make test` runs pytest
with standard JUnit and coverage reporting. The badge links expect
`reports/badges/{services,libs}/<name>/{lint,tests,coverage}.json`; publishing these
endpoints requires a separate reporting integration. The Make targets do not
generate badge JSON. An empty reports URL renders neutral `not run` badges.
Failed checks still publish test reports if documentation builds successfully.
PRs never deploy. Select `ci_sourcecraft=yes` for Sourcecraft, which runs
`make check` and retains JUnit and coverage reports.

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
separately. `enable_pages` can enable Pages only on the generated test repository;
web uses this while collecting the archive without outer deployment.
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
workflow. Automatic validation is filtered by changed paths: `src/<template>/**`
and `tests/<package>/**` select that template, while shared fixture helpers, root
dependencies/Python version, and the workflow generator select all templates.
Provider-specific workflow sources select all validations for that provider.
GitHub also watches each generated validation workflow; Sourcecraft watches its
API helper and the sources of its combined generated configuration.

Repository docs and license changes only run metatemplate checks. Seed changes
affect future templates, so they do not trigger validation of existing snapshots.
GitHub manual runs remain available. These filters are generated automatically
for new templates. GitHub compares the full PR diff and can leave path-skipped
required checks pending; see its
[path-filter documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#using-filters-to-target-specific-paths-for-pull-request-or-push-events).

Selected workflows render and scaffold via the template's test package, create a
temporary repository, wait for its configured inner CI, collect results, and
delete the repository. Results are retained as `generated-<template>-ci` on GitHub.
An inner failure fails its outer workflow. Repository tests, lint, documentation,
and generated-file checks run separately in `ci.yml`.

GitHub is the primary repository for development and pull requests. Sourcecraft
CI configuration and its integration workflow are retained; any Sourcecraft
mirror should follow GitHub.
