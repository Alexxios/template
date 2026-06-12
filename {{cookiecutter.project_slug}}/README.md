# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Development

```bash
poetry install --with dev,docs
poetry run pre-commit install
poetry run pytest
```

Run the full matrix (tests + lint + docs):

```bash
poetry run tox
```

Serve docs locally:

```bash
poetry run mkdocs serve
```

## Adding a new package

This project uses a `src/`-layout and supports multiple packages. To scaffold
one, use the nested cookiecutter template at `templates/package/` via the
helper script:

```bash
poetry run python scripts/new_package.py
# or non-interactively:
poetry run python scripts/new_package.py --no-input package_name=my_pkg description="..."
```

This creates `src/my_pkg/` and `tests/my_pkg/`, then appends the package to the
`packages` array in `pyproject.toml`. Run `poetry install` afterwards.

## License

{{cookiecutter.license}}
