"""Validate Kubernetes defaults through both stages of service generation."""

import json

import pytest
import yaml

from .test_web import generate
from .test_web import project as project


@pytest.mark.parametrize("name", ["billing_api", "on", "null", "a", "a" * 63])
def test_generated_kubernetes_resources_select_the_service_and_named_ports(project, name):
    result = generate(project, "service", name)
    assert result.returncode == 0, result.stdout + result.stderr
    member = project / "services" / name
    directory = member / "k8s"
    config = yaml.safe_load((directory / "kustomization.yaml").read_text())
    resources = {}
    for filename in config["resources"]:
        content = (directory / filename).read_text()
        assert "{{" not in content
        document = yaml.safe_load(content)
        resources[document["kind"]] = document
    assert set(resources) == {"Deployment", "Service"}
    deployment, service = resources["Deployment"], resources["Service"]
    kubernetes_name = name.replace("_", "-")
    assert deployment["metadata"]["name"] == service["metadata"]["name"] == kubernetes_name
    pod = deployment["spec"]["template"]
    labels = pod["metadata"]["labels"]
    assert labels["app.kubernetes.io/name"] == kubernetes_name
    assert deployment["spec"]["selector"]["matchLabels"].items() <= labels.items()
    assert service["spec"]["selector"].items() <= labels.items()
    assert service["spec"]["type"] == "ClusterIP"
    container = pod["spec"]["containers"][0]
    assert container["name"] == kubernetes_name
    ports = {port["name"]: port["containerPort"] for port in container["ports"]}
    service_port = service["spec"]["ports"][0]
    assert service_port["port"] == 80
    dockerfile = (member / "Dockerfile").read_text()
    command = json.loads(
        next(line[4:] for line in dockerfile.splitlines() if line.startswith("CMD "))
    )
    assert command[:4] == ["uv", "run", "--no-sync", "uvicorn"]
    assert command[command.index("--host") + 1] == "0.0.0.0"
    container_port = int(command[command.index("--port") + 1])
    assert ports[service_port["targetPort"]] == container_port == 80
    for probe, endpoint in (
        ("startupProbe", "/health/live"),
        ("readinessProbe", "/health/ready"),
        ("livenessProbe", "/health/live"),
    ):
        check = container[probe]["httpGet"]
        assert ports[check["port"]] == container_port
        assert check["path"] == endpoint
    image = config["images"][0]
    assert container["image"].split(":")[0] == image["name"] == kubernetes_name
    assert image["newName"].endswith(f"/{kubernetes_name}")
    # Deployment naming must not change the importable package or Docker entry point.
    assert (member / f"src/{name}/main.py").is_file()
    assert (member / f"src/{name}/routers/health.py").is_file()
    assert f"{name}.main:app" in command


@pytest.mark.parametrize("name", ["trailing_", "a" * 64])
def test_invalid_default_kubernetes_names_leave_no_partial_service(project, name):
    readme = (project / "README.md").read_bytes()
    result = generate(project, "service", name)
    assert result.returncode != 0
    assert "Use a Kubernetes name" in result.stdout + result.stderr
    assert [entry.name for entry in (project / "services").iterdir()] == [".gitkeep"]
    assert (project / "README.md").read_bytes() == readme
    # Library names are still governed only by Python/workspace naming rules.
    result = generate(project, "lib", name)
    assert result.returncode == 0, result.stdout + result.stderr


def test_service_template_can_override_kubernetes_name_and_preserves_existing_manifests(project):
    template = project / "templates/service/cookiecutter.json"
    context = json.loads(template.read_text())
    context["kubernetes_name"] = "custom-api"
    template.write_text(json.dumps(context))
    result = generate(project, "service", "api_")
    assert result.returncode == 0, result.stdout + result.stderr
    directory = project / "services/api_/k8s"
    for filename in ("deployment.yaml", "service.yaml"):
        assert (
            yaml.safe_load((directory / filename).read_text())["metadata"]["name"] == "custom-api"
        )
    deployment = directory / "deployment.yaml"
    custom = deployment.read_text().replace("replicas: 1", "replicas: 3")
    deployment.write_text(custom)
    context["kubernetes_name"] = "other-api"
    template.write_text(json.dumps(context))
    result = generate(project, "service", "other_api")
    assert result.returncode == 0, result.stdout + result.stderr
    assert deployment.read_text() == custom
