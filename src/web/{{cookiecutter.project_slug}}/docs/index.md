# {{cookiecutter.project_name}}

{{cookiecutter.description}}

Start with the [Developer quickstart](quickstart.md) to set up the workspace,
run a FastAPI service, and check your first change.

This is a uv workspace with independently scaffolded services and libraries.
Use `just new-service api` and `just new-lib common` to create members
and regenerate the README tables. No repository is needed to start locally.

`just check services/api` checks one member in its own environment.
`just check` checks all members and the separate integration scope.
Member pytest configuration discovers only its `tests/` and measures its `src/`.
Edit `templates/readme/*.jinja` for workspace documentation and run `just codegen`.
Member READMEs contain direct badge links and remain editable.

See [Development tools](tools.md) for the testing stack, each tool's purpose,
and setup requirements for API, database, and browser tests.

GitHub CI uses independent member jobs. See [CI reports](ci-reports.md) for
Pages layout, Allure history, and the one-time PR that binds README and template
badges and deletes its workflow and binding script. Dependabot maintains
generated project dependencies weekly.
