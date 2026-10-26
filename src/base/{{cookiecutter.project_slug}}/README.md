# {{cookiecutter.project_name}}

{{cookiecutter.description}}

{% if cookiecutter.ci_github == "yes" %}
[![Tests](https://img.shields.io/badge/dynamic/xml?url=https%3A%2F%2FOWNER.github.io%2F{{cookiecutter.project_slug}}%2Fjunit.xml&query=%2Ftestsuites%2Ftestsuite%2F%40tests&label=tests&color=blue)](https://OWNER.github.io/{{cookiecutter.project_slug}}/)
[![Coverage](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2FOWNER.github.io%2F{{cookiecutter.project_slug}}%2Fcoverage.json&query=%24.totals.percent_covered_display&label=coverage&suffix=%25&color=blue)](https://OWNER.github.io/{{cookiecutter.project_slug}}/coverage/)
{% endif %}

## Included tools

Runtime dependencies include **mashumaro** and **orjson** for serialization,
**structlog** for structured logging, and **dishka** for dependency injection.
The `dev` extra includes **pytest-profiling** for CPU profiles and
**pytest-memray** / **memray** for memory profiling on Linux/macOS.

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

{% if cookiecutter.ci_github == "yes" %}
## GitHub CI and reports

Pull requests run tests with coverage, Ruff lint/formatting, and the docs PDF
build in a separate workflow. Reports are attached to the Actions run. These
checks use a read-only token and do not run profiling, update Allure history,
or publish to Pages.

Every push to `main` or `master` runs pytest once with coverage, `pytest-profiling`,
and `pytest-memray`, then publishes the native reports to GitHub Pages. Failed
tests still publish their reports and leave the workflow failed.

### Enable Pages

1. In **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**.
2. If the `github-pages` environment restricts deployment branches, allow both
   `main` and `master`.
3. Push to `main` or `master`. No extra token or repository variable is required.
4. Replace `OWNER` in the README badges with your GitHub owner, and adjust the
   repository name or Pages domain if necessary.

Your site at `https://OWNER.github.io/{{cookiecutter.project_slug}}/` serves:

| Path | Report |
| --- | --- |
| `/` | Native Allure report with test history |
| `/coverage/` | HTML line and branch coverage |
| `/profiling/combined.svg` | CPU call graph |
| `/profiling/*.prof` | Per-test and combined CPU profiles |
| `/memory/*.html`, `/memory/*.bin` | Per-test memory flame graphs and captures |
| `/junit.xml`, `/coverage.xml`, `/coverage.json`, `/pytest.txt` | Raw reports and pytest output |
| `/history.jsonl` | Allure 3 history |

Each deployment replaces the site with the latest run from `main` or `master`.
The README badges read JUnit and coverage JSON directly through Shields.io's
[dynamic XML](https://shields.io/badges/dynamic-xml-badge) and
[dynamic JSON](https://shields.io/badges/dynamic-json-badge) APIs. They show test
count and coverage.py's combined line/branch percentage. Pages serves these
reports publicly, including coverage source listings.

Allure history uses a separate Actions cache per branch and is saved after
report generation even if tests fail. Runs are queued to serialize publishing;
cache eviction starts a new history.

To collect the same test data locally on Linux/macOS, install Graphviz
(`brew install graphviz` on macOS or `sudo apt-get install graphviz` on Ubuntu):

```bash
uv sync --extra dev
uv run pytest --profile-svg --pstats-dir=reports/profiling \
  --memray --memray-bin-path=reports/memory --memray-bin-prefix=pytest
```

Coverage and the profilers run together, so timings include instrumentation
overhead. pytest-profiling names files after test names; use unique names within
a profiling run. Generated smoke tests already have package-specific names.

## Dependency updates

Dependabot checks GitHub Actions, Python dependencies through uv, Allure CLI
through npm, and pre-commit hooks weekly and opens grouped update pull requests.
The reporting workflow installs the Allure version declared in `.github/package.json`.
Commit `uv.lock` after
running `uv sync` so updates also maintain the resolved dependency versions.

Keep `.github/dependabot.yml` on your GitHub repository's default branch to
enable updates. Python dependency updates increase the minimum version in
`pyproject.toml`, even when the new release already fits the existing range.
{% endif %}

## License

{{cookiecutter.license}}
