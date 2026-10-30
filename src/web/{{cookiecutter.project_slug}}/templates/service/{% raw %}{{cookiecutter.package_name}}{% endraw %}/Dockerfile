FROM python:{{cookiecutter.python_version}}-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Build from the workspace root to include shared libraries and uv.lock.
COPY . .
{% raw %}# Install locked runtime dependencies as non-editable packages.
RUN uv sync --locked --package {{cookiecutter.package_name}} --no-dev --no-editable
EXPOSE 80
# Start the ASGI app using the environment installed during the build.
CMD ["uv", "run", "--no-sync", "uvicorn", "{{cookiecutter.package_name}}.main:app", "--host", "0.0.0.0", "--port", "80"]{% endraw %}
