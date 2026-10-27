# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Workspace

- `services/`: independently installable applications, created with `make new-service NAME=<name>`.
- `libs/`: shared packages, created with `make new-lib NAME=<name>`.
- `tests/`: integration tests across members.
- `infra/`: Compose files, Kubernetes manifests, and nginx configuration.

Start with `make bootstrap`, scaffold members, then run `make bootstrap` again.
Run `make check` for Ruff, all workspace tests with coverage, and this documentation.
A workspace with no tests fails the test check until tests are added.

```bash
make new-service NAME=api
make new-lib NAME=common
uv add --package api ./libs/common
make bootstrap
make check
```

Each member uses a `src/` layout and has its own metadata and tests. Add runtime
dependencies with `uv add --package <name> <dependency>` and commit `uv.lock`.
Pass `DESCRIPTION="..."` to either creation target to customize the description.
The root package is virtual; tooling is configured in its `pyproject.toml`.
Service entry points are placeholders to replace with your application startup.
Customize `templates/service/` and `templates/lib/` separately. They render direct
badge links into member READMEs during creation; those files remain editable.
The workspace README is generated from `templates/readme/README.md.jinja` with
`header.md.jinja` supplying its service/library tables and badges. Edit these
templates, then run `make codegen`. Member creation runs codegen automatically;
run it after manual additions, removals, renames, or repository renames.
`make check-generated` compares the entire output with its Jinja source.

The root `pyproject.toml` remains editable. Pytest's `testpaths` are `tests`,
`services/*/tests`, and `libs/*/tests`, automatically discovering member tests
without scanning source directories or regenerating configuration.

## CI reports

GitHub Actions is the CI provider. Default-branch CI publishes this documentation,
Allure with history, and individual service/library reports. Pull requests retain
reports as artifacts without deploying or updating history. Each member badge
shows only that member's results and opens its own report.

See [GitHub Pages reports](ci-reports.md) for the directory layout, badge scope,
and history lifecycle. `make lint` and `make test` remain direct tool invocations.
