# {{cookiecutter.project_name}}

{{cookiecutter.description}}

A Python {{cookiecutter.python_min_version}}+ uv workspace. `services/` and `libs/`
start empty. Each member owns its `src/<package>/`, tests, and `pyproject.toml`;
service members also include a Dockerfile and an application entry point to implement.
The root `tests/` directory is for integration tests.

```bash
make bootstrap
uv run pre-commit install
uv run python scripts/new_service.py api
uv run python scripts/new_lib.py common
uv add --package api ./libs/common
make bootstrap
make check
```

Names above are examples. Use lowercase Python identifiers; names must be unique
across the workspace. Helpers work from any working directory and refuse to
overwrite existing members. Customize their scaffold in `templates/member/`.

Use `uv add --package <name> <dependency>` to add a member's dependencies. For
workspace dependencies, supply the local path as above; uv records the workspace
source automatically. Use `uv run --package <name> ...` to run a single member.
Commit the generated `uv.lock`. The root remains a virtual project.

`make bootstrap` installs all members and dev/docs tools, and creates `.env` from
`.env.example` if missing. Update `.env.example` when introducing settings.
`make lint`, `make format`, `make test`, `make docs`, and `make serve` are also
available. Add at least one member or integration test before `make check`;
pytest fails if the workspace has no tests.

Choose your web framework, task runner, and persistence dependencies per service.
The service entry point raises `NotImplementedError` until implemented.
See [infra/README.md](infra/README.md) for the empty Compose configuration and
container build instructions. `infra/k8s/` and `infra/nginx/` are placeholders.

GitHub CI and optional Sourcecraft CI run `make bootstrap` and `make check` and
retain JUnit and coverage reports. Pre-commit, MkDocs, and LICENSE are included.
