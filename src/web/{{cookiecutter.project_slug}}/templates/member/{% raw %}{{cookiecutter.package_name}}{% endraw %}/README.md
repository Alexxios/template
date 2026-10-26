{% raw %}# {{cookiecutter.package_name}}

{{cookiecutter.description}}

This {{cookiecutter._kind}} belongs to the parent uv workspace. Run `make bootstrap`
and `make check` from the workspace root. Add runtime dependencies with
`uv add --package {{cookiecutter.package_name}} <dependency>`.
{% if cookiecutter._kind == "service" %}
Implement `main()` in `src/{{cookiecutter.package_name}}/main.py`, then run it with
`uv run --package {{cookiecutter.package_name}} python -m {{cookiecutter.package_name}}.main`.
Build the Dockerfile using the workspace root as the context, after `uv lock`.
{% endif %}{% endraw %}