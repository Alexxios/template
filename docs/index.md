# Python Template Collection

The primary repository is [Alexxios/template on GitHub](https://github.com/Alexxios/template).
It contains a Cookiecutter metatemplate with basic tooling and a collection of
project templates under `src/`. Sourcecraft CI remains supported.

```text
templates/
├── validation/                  # Validation workflows, fixtures, README status
└── cookiecutter/
    ├── cookiecutter.json
    └── {{cookiecutter.template_name}}/
        ├── cookiecutter.json
        └── {{cookiecutter.project_slug}}/
            ├── Makefile
            ├── LICENSE
            ├── pyproject.toml
            ├── README.md
            ├── .gitignore
            ├── mkdocs.yml
            └── docs/
src/
├── base/
└── webapp/
scripts/new_template.py
scripts/sync_templates.py
tests/
├── base/
└── webapp/
docs/
pyproject.toml
Makefile
tox.ini
.pre-commit-config.yaml
mkdocs.yml
```

`scripts/new_template.py` renders the metatemplate into `src/<name>/`. It also
creates a fixture package under `tests/`, generates per-template validation
workflows for GitHub and Sourcecraft, and updates the README workflow-status
table. `scripts/sync_templates.py --check` detects stale generated files.

The project tooling seed provides
uv, Ruff, pytest, coverage, pre-commit, MkDocs, Make targets, and optional GitHub
and Sourcecraft CI. It leaves application layout and packaging to the template
author. The only content directory it supplies is the MkDocs starter `docs/`.

The existing `src/base` template still provides a Python `src/` layout, package
helper, tests, and its original tooling. New templates do not copy that layout.
The `src/webapp` template uses an empty uv workspace with `services/`, `libs/`,
package scaffolding helpers, infrastructure starters, and integration tests.

Use `make bootstrap` to install repository tooling, `make check` to run all
checks, and `make new-template NAME=python-lib` to create a template with its
validation package and workflows. `make sync-templates` refreshes generated files;
`make help` lists all targets.

Repository development uses the same basic tooling at the root. Template
payloads are tested by rendering them; they are excluded from root lint and
format commands because they contain unrendered Jinja.

See [Usage](usage.md) for generation and development commands.
