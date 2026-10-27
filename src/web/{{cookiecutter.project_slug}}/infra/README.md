# Infrastructure

## Local monitoring

Start Prometheus and Grafana from the workspace root:

```bash
docker compose -f infra/docker-compose.yml up -d
```

- Prometheus: <http://localhost:9090>. Check targets at `/targets`.
- Grafana: <http://localhost:3000>. Sign in with `admin` / `admin` and set a new
  password on first login. The Prometheus data source is provisioned automatically.

Prometheus scrapes itself every 15 seconds. In Grafana's Explore view, select
Prometheus and query `up` to verify the connection. Both ports bind to localhost.
Named volumes preserve metrics, dashboards, and Grafana's password across restarts.

Edit `prometheus/prometheus.yml` to add scrape targets and
`grafana/provisioning/datasources/prometheus.yml` to change the data source.
Restart the corresponding service after editing its configuration:

```bash
docker compose -f infra/docker-compose.yml restart prometheus
docker compose -f infra/docker-compose.yml restart grafana
```

Stop the stack with `docker compose -f infra/docker-compose.yml down`.
Adding `--volumes` also deletes the stored metrics and Grafana data.

## Application metrics

Add Compose entries when you create services. For example, a service created
with `just new-service api` can use:

```yaml
services:
  api:
    build:
      context: ..
      dockerfile: services/api/Dockerfile
    env_file: ../.env
```

Implement the service's `main()` before starting its container. Run from the
workspace root after `just bootstrap` and `uv lock` (commit `uv.lock`):

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build
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
