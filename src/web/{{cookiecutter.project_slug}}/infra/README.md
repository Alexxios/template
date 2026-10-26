# Infrastructure

The Compose files start empty. Add entries when you create services. For example,
a service created with `scripts/new_service.py api` can use:

```yaml
services:
  api:
    build:
      context: ..
      dockerfile: services/api/Dockerfile
    env_file: ../.env
```

Implement the service's `main()` before starting its container. Run from the
workspace root after `uv lock` (commit `uv.lock`):

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build
```

`k8s/` and `nginx/` are reserved for deployment manifests and proxy configuration.
