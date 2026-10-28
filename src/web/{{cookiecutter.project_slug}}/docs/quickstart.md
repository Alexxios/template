# Developer quickstart

This guide takes a freshly generated **{{cookiecutter.project_name}}** workspace
to a running FastAPI service and a passing API test. The example member names are
`api` and `common`; choose unused names if you are working in an existing repository.
Run commands from the workspace root unless a step says otherwise.

## 1. Prepare your machine

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use a
shell with Bash available for the Just recipes, such as macOS, Linux, or WSL.
Git is needed for repository hooks.

Install Docker and Docker Compose for the local infrastructure and Testcontainers
tests. On **macOS or Windows**, install and start
[Docker Desktop](https://docs.docker.com/compose/install/#docker-desktop-recommended),
which includes Docker Engine, the CLI, and Compose. On Windows, enable Docker
Desktop's WSL integration for the distribution where you run the repository commands.

On **Linux**, follow the [Docker Engine installation guide](https://docs.docker.com/engine/install/)
for your distribution to install the engine and CLI and configure Docker's package
repository. Then install the Compose plugin. For Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

For other Linux distributions, follow the
[Compose plugin installation guide](https://docs.docker.com/compose/install/linux/).
Start Docker Desktop or the Docker Engine service, then verify the plugin and
connection to the daemon:

```bash
docker compose version
docker info
```

This guide runs Compose through the `docker compose` command.

Open your generated project or clone your team's repository, then enter it:

```bash
cd {{cookiecutter.project_slug}}
uv python install {{cookiecutter.python_version}}
uv tool install rust-just
just --version
```

If `just` is missing from your shell's PATH after installation, run
`uv tool update-shell` and open a new terminal. The project's `.python-version`
selects the Python version used by uv.

## 2. Bootstrap the workspace

```bash
just bootstrap
```

This installs shared development and documentation tools, resolves the workspace
lockfile, and copies `.env.example` to `.env` when `.env` does not exist. uv manages
the virtual environments; commands below use `uv run` and Just directly.

If this is a Git checkout, enable its hooks:

```bash
uv run pre-commit install
```

For a newly generated directory, run `git init` first if you want version control
and hooks. Keep `.env` local and commit the shared `uv.lock` with dependency changes.

## 3. Start the local infrastructure

Review `.env`. PostgreSQL's database, user, and password default to `app`.
`POSTGRES_PORT` and `REDIS_PORT` can be changed before startup to avoid port conflicts.

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
docker compose --env-file .env -f infra/docker-compose.yml ps
```

PostgreSQL and Redis should report healthy. The default endpoints are:

| Service | Address from your host | Use |
| --- | --- | --- |
| PostgreSQL | `postgresql://app:app@127.0.0.1:5432/app` | Application database |
| Redis | `redis://127.0.0.1:6379/0` | Cache or task broker |
| Prometheus | <http://localhost:9090> | Metrics and scrape targets |
| Grafana | <http://localhost:3000> | Dashboards; initial login `admin` / `admin` |

All published ports bind to localhost. Change Grafana's password on first login.
Update connection URLs to match any changes to `.env`. Application containers
in the same Compose stack connect to `postgres:5432` and `redis:6379`.

Data persists in named volumes. PostgreSQL's `.env` credentials initialize an empty
database; changing them later also requires updating the existing database.
See `infra/README.md` for connection details, health-based startup dependencies,
and application metrics configuration.

## 4. Create a service and shared library

```bash
just new-service api "HTTP API"
just new-lib common "Shared application code"
uv add --package api ./libs/common
uv add --package api fastapi uvicorn
just bootstrap
```

The generators create installable packages with their own `pyproject.toml`,
`src/`, and `tests/`, and refresh the workspace README. The service also gets a
Dockerfile and a placeholder `main()` to implement. The library is ready for
shared code as the application grows.

Declare runtime dependencies on the member that imports them, even when they also
appear in the root manifest. Member tests and container builds install that
member's declared dependencies. Shared dev tools come from the root `dev` group.
See [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) for
the shared lockfile and member dependency model.

## 5. Implement and run the API

Replace the placeholder in `services/api/src/api/main.py` with:

```python
import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
```

The `main()` function supports the scaffolded Dockerfile's `python -m api.main`
entry point. For local development, start a server bound to localhost with reload:

```bash
uv run --package api uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir services/api/src --reload-dir libs/common/src
```

Keep that terminal running. In a second terminal, request the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expect `{"status":"ok"}`. Open <http://127.0.0.1:8000/docs> for interactive API docs
or <http://127.0.0.1:8000/openapi.json> for the schema. This follows FastAPI's
[first steps](https://fastapi.tiangolo.com/tutorial/first-steps/).

The example endpoint does not access a database. When adding persistence, declare
the chosen database drivers on `api`, configure connections using the addresses
above, and add your application's migrations.

## 6. Add a test and run checks

Create `services/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from api.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run from the workspace root:

```bash
just format services/api
just check services/api
just check
```

The API test calls the application in process and can run with the local server
stopped. `just check services/api` lints and tests that member. `just check` also
checks the library, integration tests, generated README, and documentation.
An empty root integration suite is allowed; each member should have tests.

Put library tests in `libs/common/tests/` and cross-member tests in the root
`tests/`. Use `just test libs/common` or `just test integration` to select a scope.
Each test scope has its own environment under `.venvs/` and reports under
`reports/<scope>/`. For example, API coverage is at
`reports/services/api/coverage/index.html`.

The [Development tools](tools.md) guide covers Hypothesis, RESPX, Schemathesis,
Testcontainers, and browser setup. Testcontainers fixtures manage disposable
databases independently of the local Compose stack.

## 7. Preview documentation and reports

Build the docs, then serve them on a different port from the API:

```bash
just docs
uv run --group docs mkdocs serve --dev-addr 127.0.0.1:8001
```

Open <http://127.0.0.1:8001>. When port 8000 is free, `just serve` is the shorter
command for the default documentation server.

After running checks, `just reports` builds report pages and badges from the
existing results. CI also builds the Allure reports and publishes the default
branch's documentation and reports. Follow [CI reports](ci-reports.md) when
enabling GitHub Pages and binding the README badges.

## 8. Use the daily workflow

After pulling changes, run `just bootstrap` to refresh tools and dependencies.
For each change:

```bash
just format
just check
```

Edit `templates/readme/*.jinja` to change the generated workspace README, then
run `just codegen`. Run it after manual member additions, removals, or renames
too. Individual member READMEs remain editable. Commit source changes, manifests,
`uv.lock`, docs, and generated README updates together.

## 9. Stop local services

Use Ctrl+C in the API and docs terminals. Stop the infrastructure from the
workspace root:

```bash
docker compose --env-file .env -f infra/docker-compose.yml down
```

Named volumes retain the local data. Adding `--volumes` deletes database, Redis,
metrics, and Grafana data; use that only when intentionally resetting the stack.
