# Infrastructure

## Local stack

Start PostgreSQL, Redis, Prometheus, and Grafana from the workspace root.
`just bootstrap` creates `.env` from `.env.example` if it is missing:

```bash
just bootstrap
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
```

| Service | Local address | Purpose / defaults |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:5432` | Application database. Database, user, and password default to `app`. |
| Redis | `127.0.0.1:6379` | Cache, task broker, or other application state. No password in the local starter. |
| Prometheus | <http://localhost:9090> | Metrics storage; check scrape targets at `/targets`. |
| Grafana | <http://localhost:3000> | Dashboards; sign in with `admin` / `admin` and change the password on first login. |

All published ports bind to localhost. These credentials are local development
defaults. Edit `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_PORT`, and `REDIS_PORT` in `.env` to customize database settings or
avoid host port conflicts. The `--env-file .env` option explicitly loads the
workspace settings even though the Compose files live under `infra/`.

Named volumes preserve PostgreSQL data, Redis data, metrics, dashboards, and
Grafana's password across restarts. Redis enables append-only persistence.
The PostgreSQL volume mounts at `/var/lib/postgresql`, as required by the
[PostgreSQL 18+ image layout](https://hub.docker.com/_/postgres).
PostgreSQL's database/user/password settings initialize an empty volume; changing
them later requires updating the existing database as well.

Stop the stack with:

```bash
docker compose --env-file .env -f infra/docker-compose.yml down
```

Adding `--volumes` also deletes all stored database, Redis, metrics, and Grafana data.

## Database connections

With the default `.env`, applications running on the host can use
`postgresql://app:app@127.0.0.1:5432/app` and `redis://127.0.0.1:6379/0`.
Applications in the same Compose stack use `postgres:5432` and `redis:6379`;
host port overrides do not change these container ports. Adjust the credentials
and database in connection URLs when changing `.env`.

Declare the application's chosen database drivers in its member dependencies,
and configure connections and migrations in the application. PostgreSQL and Redis
have health checks, so application services can wait for `service_healthy`, as in
the example below.

For automated tests, Testcontainers fixtures create their own disposable databases
and return their connection details. Those tests can run independently of this
persistent development stack.

## Local monitoring

Prometheus scrapes itself every 15 seconds. In Grafana's Explore view, select
Prometheus and query `up` to verify the connection. Grafana's Prometheus data
source is provisioned automatically.

Edit `prometheus/prometheus.yml` to add scrape targets and
`grafana/provisioning/datasources/prometheus.yml` to change the data source.
Restart the corresponding service after editing its configuration:

```bash
docker compose --env-file .env -f infra/docker-compose.yml restart prometheus
docker compose --env-file .env -f infra/docker-compose.yml restart grafana
```

## Application metrics

Add Compose entries to `docker-compose.dev.yml` when you create services.
For example, a service created with `just new-service api` can use:

```yaml
services:
  api:
    build:
      context: ..
      dockerfile: services/api/Dockerfile
    env_file: ../.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

Implement the service's `main()` before starting its container. Run from the
workspace root after `just bootstrap` and `uv lock` (commit `uv.lock`):

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build
```

Once the API listens on `0.0.0.0:8000` and exposes a Prometheus-format `/metrics`
endpoint, append this job to `scrape_configs` in `prometheus/prometheus.yml`:

```yaml
  - job_name: api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8000"]
```

Use the Compose service name and its container port. Installing Python packages
alone does not expose an endpoint; configure it in the application. Restart
Prometheus after adding the job, then check `/targets`. Add one job per service.

The image versions are pinned in `docker-compose.yml` and updated by Dependabot.
See the [Prometheus configuration reference](https://prometheus.io/docs/prometheus/latest/configuration/)
and [Grafana provisioning guide](https://grafana.com/docs/grafana/latest/administration/provisioning/)
for additional settings.

`k8s/` and `nginx/` are reserved for deployment manifests and proxy configuration.
