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
It includes a justfile, LICENSE, pre-commit, MkDocs, and Python tooling.

```bash
cd <project_slug>
uv tool install rust-just
just bootstrap
just new-service api
just new-lib common
uv add --package api ./libs/common
just bootstrap
just check
```

Choose your own member names and application framework. A service owns its
`src/<name>/`, tests, `pyproject.toml`, and Dockerfile. A library has the same Python
layout without a container. Service entry points are placeholders to implement.
The root `tests/` is for integration tests across members. Creation commands
refuse duplicate names. Pass a second argument, such as
`just new-lib common "Shared utilities"`, for a custom description.
Use `just --justfile /path/to/workspace/justfile new-service api` from another directory.
Customize `templates/service/` and
`templates/lib/` independently; libraries never include service-only files.

Each member has editable pytest configuration for its own `tests/` and `src/`.
Root pytest configuration is for integration tests. `just check services/api`
checks one member; `just check` runs all members and integration separately.
Each test scope uses a separate environment and produces its own native reports.
Shared tooling is installed by `just bootstrap`; commit the shared `uv.lock`.

The web template supports GitHub Actions only and asks for no repository or URL.
Badges start as **not published**. After enabling GitHub Actions as the Pages
source, the one-time setup workflow opens a PR binding README links to the actual
Pages URL. That PR also binds the service, library, and workspace README templates
and deletes both its workflow and `scripts/bind_badges.py`. Future members render
links directly from the templates. It uses the built-in `GITHUB_TOKEN`; enable
**Allow GitHub Actions to create and approve pull requests** under
Settings → Actions → General.
No custom token or secret is required. The setup PR's checks may await approval.

Pants discovers CI targets and infers dependencies from Python imports using each
member's scaffolded `BUILD` file. PRs check changed members and their transitive
dependents, plus integration. Shared changes, deletions, and default-branch runs
check every member. Jobs use `fail-fast: false`; uv and Just still execute checks.
Use `pants dependencies --transitive services/api:member` or
`pants dependents --transitive libs/common::` to inspect the native graph.
Declare relationships that cannot be inferred from imports explicitly in `BUILD`.
A reporting job collects artifacts and builds member pages, badges, coverage,
and separate Allure reports/history under `/reports/services/<name>/` and
`/reports/libs/<name>/`. Integration results stay under `/reports/integration/`
and do not contribute to member coverage badges. Default-branch CI deploys Pages;
PRs retain artifacts without deploying or updating history. Failed checks still
publish results when report generation succeeds, while keeping failure status.

Creation refreshes the workspace README through its Jinja templates. Normal
`just codegen` preserves existing member READMEs; the setup script only changes
badge lines. See the generated `docs/ci-reports.md` for the full lifecycle.
Dependabot updates Python dependencies, Actions, hooks, Allure, and service images.

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

For templates with a `[sourcecraft]` validation section, select `--ci sourcecraft`
to generate a Sourcecraft fixture. The web fixture accepts GitHub only. The default scaffold
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

Base and metatemplate projects use `make bootstrap` to install development and
documentation dependencies. Their Makefile also offers `lint`, `format`, `test`,
`docs`, `serve`, and `check`. Web workspaces use the justfile commands described above.
Add application code and tests before running `make check`; pytest reports an
error if there are no tests. Enable packaging and select a build backend when
your chosen layout needs an installable package.

GitHub CI is enabled by default. Base and metatemplate projects also support
Sourcecraft via `ci_sourcecraft=yes`; web projects use GitHub only. The basic CI configurations run
the same commands as local development.

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

Each template has an independent GitHub validation workflow. Templates declaring
Sourcecraft support also have a Sourcecraft validation workflow. Automatic validation is filtered by changed paths: `src/<template>/**`
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
