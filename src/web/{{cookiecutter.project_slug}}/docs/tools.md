# Development tools

Run `just bootstrap` to install the shared `dev` and `docs` dependency groups
from the workspace's `pyproject.toml`. The testing tools are available in each
member's isolated test environment and in the integration environment.

## Testing

| Testing type | Tools | Purpose |
| --- | --- | --- |
| Unit / integration | [pytest](https://docs.pytest.org/) + [HTTPX](https://www.python-httpx.org/) (`pytest`, `httpx`) | Run tests and fixtures; exercise FastAPI through its HTTPX-based `TestClient`, or use `AsyncClient` with `ASGITransport` for async API tests. |
| API fuzzing | [Schemathesis](https://schemathesis.readthedocs.io/) (`schemathesis`) | Generate requests from FastAPI's OpenAPI schema to find server errors, schema violations, and unexpected behavior. |
| Edge cases / property testing | [Hypothesis](https://hypothesis.readthedocs.io/) (`hypothesis`) | Generate inputs and shrink failing examples. Define strategies that express the constraints of your Pydantic models, including custom validation rules. |
| Mocking outbound APIs | [RESPX](https://lundberg.github.io/respx/) (`respx`) | Mock outgoing synchronous and asynchronous HTTPX requests, control responses, and assert calls without contacting external APIs. |
| Database integration | [Testcontainers](https://testcontainers-python.readthedocs.io/) (`testcontainers[postgres,redis]`) | Start real PostgreSQL and Redis containers for tests. Requires Docker; your application's database driver determines whether connections are async. |
| Browser end-to-end | [Playwright](https://playwright.dev/python/) + [pytest-playwright](https://playwright.dev/python/docs/test-runners) (`playwright`, `pytest-playwright`) | Test browser workflows with isolated browser fixtures. Playwright offers sync and async APIs; the included pytest plugin provides sync fixtures and failure video capture. |

Place member tests in `services/<name>/tests/` or `libs/<name>/tests/`, and
cross-member integration tests in the root `tests/` directory. Run them with:

```bash
just test services/api
just test integration
just test
```

For async API tests, use `@pytest.mark.anyio` with HTTPX's `AsyncClient` and
`ASGITransport`. AnyIO is installed through HTTPX; set the `anyio_backend`
fixture to `"asyncio"` when the application uses asyncio drivers. Manage the
application's lifespan explicitly when startup or shutdown hooks are required.
See the [FastAPI async testing guide](https://fastapi.tiangolo.com/advanced/async-tests/).

Hypothesis does not automatically satisfy every Pydantic constraint or custom
validator. Use explicit strategies for valid model inputs and separate cases
that check validation failures.

To fuzz a running local API that exposes `/openapi.json`:

```bash
uv run --group dev schemathesis run http://127.0.0.1:8000/openapi.json
```

Use a disposable test application and database: generated requests can create,
change, and delete data. Service scaffolds provide `/health/live` and `/health/ready`;
implement and start the application before running this command.

Testcontainers needs a running Docker daemon locally and in CI. Create and clean
up containers in fixtures or context managers, and declare your application's
chosen database driver in the member's dependencies. The PostgreSQL and Redis
extras are included in the shared dev group; they do not configure application
connections or migrations.

For local development, `infra/docker-compose.yml` provides persistent PostgreSQL
and Redis services alongside Prometheus and Grafana. See `infra/README.md` for
startup commands and connection settings. Testcontainers fixtures create their
own disposable databases and can run independently of the development stack.

Before running browser tests, install Chromium and start the application:

```bash
uv run --group dev python -m playwright install chromium
```

On Linux CI, use `playwright install --with-deps chromium` to install browser
system dependencies too. For async browser fixtures, follow Playwright's
[async fixture setup](https://playwright.dev/python/docs/test-runners#async-fixtures),
which requires the additional `pytest-playwright-asyncio` plugin and loop
configuration. See [Browser failure videos](ci-reports.md#browser-failure-videos)
for the included sync fixtures' recording and Allure integration.

## Workspace tooling

| Tool | Purpose | Availability / command |
| --- | --- | --- |
| uv | Manage dependencies, the shared lockfile, and isolated environments. | Install uv first; `just bootstrap` runs `uv sync`. Also declared in `dev`. |
| Just | Run the workspace's development commands. | Install with `uv tool install rust-just`; run `just` to list recipes. |
| Cookiecutter + Jinja2 | Scaffold services and libraries and render the workspace README. | `dev`; `just new-service`, `just new-lib`, `just codegen`. |
| Ruff | Lint and format Python code. | `dev`; `just lint`, `just format`. |
| pytest-cov + coverage.py | Measure line and branch coverage and produce HTML, JSON, and XML reports per scope. | `dev`; enabled by `just test`. |
| allure-pytest | Record test results and attachments for Allure reports. | `dev`; enabled by `just test`. CI installs the Allure CLI separately to build reports. |
| pre-commit | Run repository hooks before commits. | `dev`; enable with `uv run pre-commit install`. |
| MkDocs + Material | Build and serve the project's documentation. | `docs`; `just docs`, `just serve`. |
| Pants | Infer member dependencies and select affected CI targets. | Launcher installed separately; configured by `pants.toml` and member `BUILD` files. |

See [CI reports](ci-reports.md) for report paths, publication, and history.
