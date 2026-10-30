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
just bootstrap
```

The generators create installable packages with their own `pyproject.toml`,
`src/`, and `tests/`, and refresh the workspace README. The service also gets a
Dockerfile, a FastAPI `app`, and `k8s/` defaults for Kubernetes. FastAPI and Uvicorn
are already declared in the service's dependencies.
The library is ready for shared code as the application grows.

Declare runtime dependencies on the member that imports them, even when they also
appear in the root manifest. Member tests and container builds install that
member's declared dependencies. Shared dev tools come from the root `dev` group.
See [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/) for
the shared lockfile and member dependency model.

## 5. Implement and run the API

The service separates application assembly from route groups:

```text
services/api/
├── pyproject.toml
├── Dockerfile
├── k8s/
├── tests/
└── src/api/
    ├── __init__.py
    ├── main.py
    ├── py.typed
    └── routers/
        ├── __init__.py
        └── health.py
```

`main.py` defines `create_app()`, the application lifespan, and the ASGI `app`.
`routers/health.py` provides `/health/live` and `/health/ready`. Add new route
groups under `routers/` and register them with `app.include_router()` inside
`create_app()`. See [FastAPI's router guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/).

`src/` is a source directory; `api` is the import package. This keeps imports
distinct across workspace services and separates installed code from project
tooling. See the [Python layout comparison](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

The Dockerfile starts Uvicorn directly on port 80:

```bash
uv run --no-sync uvicorn api.main:app --host 0.0.0.0 --port 80
```

The import path includes `api` because the application lives in an installed
workspace package. `--no-sync` uses the dependencies installed during the image
build. See [uv's syncing options](https://docs.astral.sh/uv/concepts/projects/sync/)
and the [FastAPI server guide](https://fastapi.tiangolo.com/deployment/manually/).
For local development, use port 8000 on localhost with reload:

```bash
uv run --package api uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir services/api/src --reload-dir libs/common/src
```

Keep that terminal running. In a second terminal, request the health endpoint:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

Expect `{"status":"ok"}` and `{"status":"ready"}`, respectively.
Open <http://127.0.0.1:8000/docs> for interactive API docs
or <http://127.0.0.1:8000/openapi.json> for the schema. This follows FastAPI's
[first steps](https://fastapi.tiangolo.com/tutorial/first-steps/).

Readiness returns 503 while `app.state.ready` is false. Initialize required
resources in the lifespan before setting it true, and clean up resources on
shutdown. The default readiness check covers application lifecycle only; add
bounded checks for essential dependencies as the service grows. Keep liveness
independent of database availability. When adding persistence, declare the chosen
drivers on `api`, configure connections using the addresses above, and add your
application's migrations.

For Kubernetes deployment, follow `services/api/README.md` to build and push the
image, configure Kustomize, and apply the manifests. The container defaults use port 80
with HTTP startup/readiness/liveness probes and a cluster-internal Service.
Startup and liveness use `/health/live`; readiness uses `/health/ready`.
Review resource limits and configure the application's environment before
deploying; the local Compose databases are separate from the cluster.

## 6. Add a test and run checks

Create `services/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from api.main import create_app


def test_health():
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json() == {"status": "ready"}
        app.state.ready = False
        assert client.get("/health/ready").status_code == 503
        assert client.get("/health/live").status_code == 200
    assert app.state.ready is False
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
