"""Exercise real uv environments to catch undeclared sibling dependencies."""

import http.client
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from .test_web import JUST, generate
from .test_web import project as project


def test_member_environment_requires_declared_workspace_dependencies(project):
    for name in ("consumer", "provider", "unrelated"):
        assert generate(project, "lib", name).returncode == 0
    test = project / "libs/consumer/tests/test_smoke.py"
    test.write_text(
        "import importlib.util\n\nimport provider\n\n\n"
        "def test_dependencies():\n"
        "    assert provider is not None\n"
        '    assert importlib.util.find_spec("unrelated") is None\n'
    )
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    uv = Path(sys.prefix) / "bin/uv"
    env["UV"] = str(uv if uv.exists() else shutil.which("uv"))
    command = [JUST, "test", "libs/consumer"]
    broken = subprocess.run(
        command, cwd=project, env=env, capture_output=True, text=True, timeout=120
    )
    assert broken.returncode != 0
    assert "No module named 'provider'" in broken.stdout, broken.stdout + broken.stderr
    manifest = project / "libs/consumer/pyproject.toml"
    manifest.write_text(
        manifest.read_text().replace("dependencies = []", 'dependencies = ["provider"]')
        + "\n[tool.uv.sources]\nprovider = { workspace = true }\n"
    )
    fixed = subprocess.run(
        command, cwd=project, env=env, capture_output=True, text=True, timeout=120
    )
    assert fixed.returncode == 0, fixed.stdout + fixed.stderr
    assert "1 passed" in fixed.stdout
    assert (project / ".venvs/libs/consumer/pyvenv.cfg").is_file()
    assert not (project / ".venvs/libs/provider").exists()


def test_service_docker_command_serves_the_generated_app_from_installed_dependencies(project):
    result = generate(project, "service", "billing_api")
    assert result.returncode == 0, result.stdout + result.stderr
    member = project / "services/billing_api"
    dockerfile = (member / "Dockerfile").read_text().splitlines()
    # On case-insensitive hosts, Pants' BUILD file blocks setuptools' build/ directory.
    # Docker's Linux filesystem does not have this collision.
    if (member / "build").is_file():
        (member / "BUILD").unlink()
    uv = str(Path(sys.prefix) / "bin/uv")
    # Match the Docker build's dependency installation, including non-editable packages.
    install = shlex.split(next(line[4:] for line in dockerfile if line.startswith("RUN ")))
    for args in (["lock"], install[1:]):
        result = subprocess.run(
            [uv, *args], cwd=project, capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, result.stdout + result.stderr
    lifecycle_check = """\
import asyncio

from fastapi import HTTPException, Request

from billing_api.main import create_app
from billing_api.routers.health import liveness, readiness


async def check():
    app, other = create_app(), create_app()
    request = Request({"type": "http", "app": app})

    async def expect_unready():
        try:
            await readiness(request)
        except HTTPException as exc:
            assert exc.status_code == 503
        else:
            raise AssertionError("An unavailable service must reject readiness checks")

    await expect_unready()
    async with app.router.lifespan_context(app):
        assert await readiness(request) == {"status": "ready"}
        assert other.state.ready is False
        app.state.ready = False
        await expect_unready()
        assert await liveness() == {"status": "ok"}
        app.state.ready = True
    await expect_unready()


asyncio.run(check())
"""
    result = subprocess.run(
        [uv, "run", "--no-sync", "python", "-c", lifecycle_check],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    command = json.loads(next(line[4:] for line in dockerfile if line.startswith("CMD ")))
    command[0] = uv
    # Use an available localhost port so the test does not require privileged ports.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    command[command.index("--port") + 1] = str(port)
    command[command.index("--host") + 1] = "127.0.0.1"
    log = project / "server.log"
    with log.open("w") as output:
        process = subprocess.Popen(
            command,
            cwd=project,
            env={
                **{key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
                "UV_OFFLINE": "1",
            },
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(log.read_text())
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
                try:
                    for endpoint, status in (("/health/live", "ok"), ("/health/ready", "ready")):
                        connection.request("GET", endpoint)
                        response = connection.getresponse()
                        assert response.status == 200
                        assert json.loads(response.read()) == {"status": status}
                    break
                except OSError:
                    time.sleep(0.05)
                finally:
                    connection.close()
            else:
                pytest.fail(f"Uvicorn did not become ready:\n{log.read_text()}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
