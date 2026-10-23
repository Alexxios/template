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

{% if cookiecutter.ci_github == "yes" %}
## Test history in GitHub CI

The test job restores `.allure/history.jsonl` before running tests and appends
the current results when building the Allure 3 report. It saves history even
when tests fail and uploads it as the `allure-history` artifact alongside the
`allure-report` artifact. No additional secrets are required.

Each branch or pull request keeps its own history. A new history starts from
the default branch's latest cached history when available. Pull request results
do not update the default branch's history. Test jobs for the same ref run one
at a time to avoid overwriting each other's updates.

History persists through GitHub Actions caches, which GitHub may evict after
seven days without access or when storage limits are reached. If no cache is
available, the next report starts a new history. The `allure-history` artifact
also provides a downloadable copy for each run that builds a report.

To accumulate history locally with Node.js 24 or later installed:

```bash
uv run pytest
npx --yes allure@3 awesome allure-results --single-file --output allure-report \
  --history-path .allure/history.jsonl
```

## Dependency updates

Dependabot checks GitHub Actions, Python dependencies through uv, and pre-commit
hooks weekly and opens grouped update pull requests. Commit `uv.lock` after
running `uv sync` so updates also maintain the resolved dependency versions.

Keep `.github/dependabot.yml` on your GitHub repository's default branch to
enable updates. Python dependency updates increase the minimum version in
`pyproject.toml`, even when the new release already fits the existing range.
{% endif %}

## License

{{cookiecutter.license}}
