# Python Template Collection

This repository is a metatemplate: it contains project templates and a helper
for creating new ones. Templates live under `src/`; each directory is a complete
Cookiecutter template with its own configuration, hooks, and project files.

```text
src/
└── base/
    ├── cookiecutter.json
    ├── hooks/
    ├── templates/dependencies/pyproject.toml
    └── {{cookiecutter.project_slug}}/
scripts/new_template.py
tests/
docs/
pyproject.toml
tox.ini
.pre-commit-config.yaml
mkdocs.yml
```

The `base` starter provides the existing Python `src/` layout, package helper,
uv configuration, tests, Ruff, pre-commit, tox, MkDocs, license selection, and
optional GitHub, Sourcecraft, and GitLab CI.

Repository development uses the same basic tooling at the root. Template
payloads are tested by rendering them; they are excluded from root lint and
format commands because they contain unrendered Jinja.

See [Usage](usage.md) for generation and development commands.
