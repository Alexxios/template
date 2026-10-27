FROM python:{{cookiecutter.python_version}}-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY . .
{% raw %}RUN uv sync --locked --package {{cookiecutter.package_name}} --no-dev --no-editable
CMD [".venv/bin/python", "-m", "{{cookiecutter.package_name}}.main"]{% endraw %}
