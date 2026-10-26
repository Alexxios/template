# {{cookiecutter.project_name}}

{{cookiecutter.description}}

## Development

Install Python {{cookiecutter.python_version}}, uv, and Make, then run:

```bash
make bootstrap
make help
```

The tooling supports your chosen application layout. Add code and tests before
running `make check`; pytest reports an error when no tests exist. Test discovery
uses pytest's standard file naming conventions. Add a build backend and enable
packaging in `pyproject.toml` if this project needs an installable package.

```bash
make lint
make test
make docs
make serve
```

The equivalent commands are defined in `Makefile`; they use uv, Ruff, pytest,
coverage, and MkDocs. After initializing Git, enable the included pre-commit hooks:

```bash
uv run pre-commit install
```

Commit `uv.lock` after syncing dependencies. Coverage and JUnit reports are
written to `reports/`.

{% if cookiecutter.ci_github == "yes" %}
## GitHub CI

Pushes to `main`/`master` and pull requests run `make check`. Test and coverage
reports are retained as workflow artifacts, including after failed tests.
{% endif %}
{% if cookiecutter.ci_sourcecraft == "yes" %}
## Sourcecraft CI

Sourcecraft runs the same Make targets on pushes to `main`/`master` and pull
requests. Configuration is in `.sourcecraft/ci.yaml`.
{% endif %}

## License

{{cookiecutter.license}}
