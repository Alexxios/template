# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Development

```bash
uv sync --extra dev --extra docs
uv run pre-commit install
uv run pytest
```

Run the full matrix (tests + lint + docs):

```bash
uv run tox
```

Serve docs locally:

```bash
uv run mkdocs serve
```

## Adding a new package

This project uses a `src/`-layout and supports multiple packages. To scaffold
one, use the nested cookiecutter template at `templates/package/` via the
helper script:

```bash
uv run python scripts/new_package.py
# or non-interactively:
uv run python scripts/new_package.py --no-input package_name=my_pkg description="..."
```

This creates `src/my_pkg/` and `tests/my_pkg/`. Packages are auto-discovered
by setuptools under `src/`, so no manual `pyproject.toml` registration is needed.
Run `uv sync` afterwards to refresh the environment.

## License

{{cookiecutter.license}}
