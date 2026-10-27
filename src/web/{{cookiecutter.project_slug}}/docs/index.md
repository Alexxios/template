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
run it after manual additions, removals, renames, or reports URL changes.
`make check-generated` compares the entire output with its Jinja source.

The root `pyproject.toml` remains editable. Pytest's `testpaths` are `tests`,
`services/*/tests`, and `libs/*/tests`, automatically discovering member tests
without scanning source directories or regenerating configuration.

## CI reports

GitHub pull requests run `pull-request.yml` and retain `check-reports`. The default
branch runs `ci.yml` and also uploads `github-pages`, a Pages artifact containing
this documentation site and the test reports. After extracting its `artifact.tar`,
open `index.html` for the docs or `reports/coverage/index.html` for coverage.
Raw reports are at `reports/junit.xml`, `reports/coverage.xml`, and
`reports/coverage.json`. `make lint` runs Ruff and its formatting check directly;
`make test` runs pytest with standard JUnit and coverage reporting.

Badge links expect per-member JSON endpoints under
`reports/badges/{services,libs}/<name>/`. Publishing these requires a separate
reporting integration; the Make targets do not generate badge JSON.

The default branch is read from the repository settings, so renaming it does not
require editing the workflow. CI automatically deploys this site and reports to
GitHub Pages, including after failed lint/tests if the docs build succeeds. PRs
retain reports without deploying. Set the repository's Pages source to **GitHub
Actions** once and provide `github_repository=owner/repo` during generation.
The default public reports URL is stored in `tool.codegen.reports_url`.
Change it and run `make codegen` when using a custom domain, and update existing
member README links directly. Shields requires publicly accessible endpoints.
