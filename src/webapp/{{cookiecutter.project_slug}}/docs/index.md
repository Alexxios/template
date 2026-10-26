# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Workspace

- `services/`: independently installable applications, created with `scripts/new_service.py`.
- `libs/`: shared packages, created with `scripts/new_lib.py`.
- `tests/`: integration tests across members.
- `infra/`: Compose files, Kubernetes manifests, and nginx configuration.

Start with `make bootstrap`, scaffold members, then run `make bootstrap` again.
Run `make check` for Ruff, all workspace tests with coverage, and this documentation.
A workspace with no tests fails the test check until tests are added.

```bash
uv run python scripts/new_service.py api
uv run python scripts/new_lib.py common
uv add --package api ./libs/common
make bootstrap
make check
```

Each member uses a `src/` layout and has its own metadata and tests. Add runtime
dependencies with `uv add --package <name> <dependency>` and commit `uv.lock`.
The root package is virtual; tooling is configured in its `pyproject.toml`.
Service entry points are placeholders to replace with your application startup.
