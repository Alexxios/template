{% raw %}"""Only service packages need an executable entry point and a container."""

from pathlib import Path

if "{{cookiecutter._kind}}" != "service":
    Path("Dockerfile").unlink()
    Path("src/{{cookiecutter.package_name}}/main.py").unlink()
{% endraw %}