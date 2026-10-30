{% raw %}# {{cookiecutter.package_name}}

![lint](https://img.shields.io/badge/lint-not%20published-lightgrey)
![tests](https://img.shields.io/badge/tests-not%20published-lightgrey)
![coverage](https://img.shields.io/badge/coverage-not%20published-lightgrey)

{{cookiecutter.description}}

Run `just check services/{{cookiecutter.package_name}}` from the workspace root.
Add dependencies with `uv add --package {{cookiecutter.package_name}} <dependency>`.

## Structure

```text
src/{{cookiecutter.package_name}}/
├── __init__.py
├── main.py              # Application factory, lifespan, and ASGI app
├── py.typed
└── routers/
    ├── __init__.py
    └── health.py        # Liveness and readiness routes
```

`src/` separates installable Python code from tests and project tooling.
`{{cookiecutter.package_name}}` is the import package, so imports use
`{{cookiecutter.package_name}}.routers`, without `src` in the module path.
The package name also keeps services' modules distinct in workspace integration
tests. See the [Python layout comparison](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

`main.py` assembles the application with `create_app()` and registers routers.
Add route groups under `routers/` and include them in the factory. Initialize
required resources in `lifespan()` before setting `app.state.ready = True`;
close them during cleanup. Each application instance has its own readiness state.

## Server

`src/{{cookiecutter.package_name}}/main.py` exposes the FastAPI `app`.
The Dockerfile starts it with:

```bash
uv run --no-sync uvicorn {{cookiecutter.package_name}}.main:app --host 0.0.0.0 --port 80
```

FastAPI and Uvicorn are declared as service dependencies. The image installs
them from the workspace lockfile at build time; `--no-sync` reuses that environment
at startup. For local development, run from the workspace root:

```bash
uv run --package {{cookiecutter.package_name}} uvicorn {{cookiecutter.package_name}}.main:app --host 127.0.0.1 --port 8000 --reload
```

## Health checks

| Endpoint | Successful response | Purpose |
| --- | --- | --- |
| `GET /health/live` | `200 {"status":"ok"}` | The application can respond. Keep it independent of external services. |
| `GET /health/ready` | `200 {"status":"ready"}` | This instance has finished initialization and can accept traffic. Returns 503 when `app.state.ready` is false. |

Readiness starts false, becomes true during startup, and resets during lifespan
cleanup. The default checks application lifecycle only. Add bounded checks for
required dependencies in `routers/health.py`; return 503 if an essential dependency
is unavailable. A database outage should not make the liveness endpoint fail.

## Kubernetes

`k8s/` contains a Deployment, a ClusterIP Service, and a Kustomize configuration.
The Kubernetes resource name is `{{cookiecutter.kubernetes_name}}`; the Python
package and workspace directory remain `{{cookiecutter.package_name}}`.

Uvicorn listens on `0.0.0.0:80` in the container. The Service routes port 80 to
the container's named `http` port. Startup and liveness probes request
`/health/live`; readiness requests `/health/ready`. A failed readiness probe
stops Service traffic, while repeated startup or liveness failures restart the
container. For a worker without HTTP endpoints, remove the
Service from `kustomization.yaml`, remove or replace the ports and HTTP probes,
and replace the Uvicorn command in the Dockerfile with the worker command.

The Deployment starts one replica, requesting 100m CPU and 128Mi memory with
limits of 500m CPU and 256Mi memory. Adjust resources, replica count, ports, and
probes for the application. Configure application environment variables and
Secret references in `deployment.yaml`; the local Compose stack and `.env` are
not provisioned in Kubernetes.

Set `images[].newName` and `newTag` in `k8s/kustomization.yaml` to your image
repository and an immutable release tag. Replace the example registry and tag
in these commands to match. Build from the workspace root so local libraries
and the shared lockfile are available:

```bash
uv lock
docker build -f services/{{cookiecutter.package_name}}/Dockerfile -t registry.example.com/your-team/{{cookiecutter.kubernetes_name}}:dev .
docker push registry.example.com/your-team/{{cookiecutter.kubernetes_name}}:dev
kubectl kustomize services/{{cookiecutter.package_name}}/k8s
kubectl apply -n default -k services/{{cookiecutter.package_name}}/k8s
kubectl rollout status -n default deployment/{{cookiecutter.kubernetes_name}}
kubectl port-forward -n default service/{{cookiecutter.kubernetes_name}} 8080:80
```

Use your intended kubectl context and replace `default` with an existing target
namespace. For private registries, configure `imagePullSecrets` in the Deployment.
The Service is cluster-internal; port forwarding exposes it at
<http://localhost:8080> for local testing. Shared environment overlays can live
under `infra/k8s/`. See the
[Kustomize guide](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/)
for image overrides and overlays, and the
[probe guide](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
for application health checks.
{% endraw %}
