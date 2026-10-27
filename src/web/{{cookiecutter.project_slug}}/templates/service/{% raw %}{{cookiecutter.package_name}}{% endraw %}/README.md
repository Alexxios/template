{% raw %}# {{cookiecutter.package_name}}

{% if cookiecutter.reports_url -%}
[![lint](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/services/" ~ cookiecutter.package_name ~ "/lint.json") | urlencode }})]({{cookiecutter.reports_url}}/lint.json)
[![tests](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/services/" ~ cookiecutter.package_name ~ "/tests.json") | urlencode }})]({{cookiecutter.reports_url}}/tests.json)
[![coverage](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/services/" ~ cookiecutter.package_name ~ "/coverage.json") | urlencode }})]({{cookiecutter.reports_url}}/coverage/index.html)
{% else -%}
![lint](https://img.shields.io/badge/lint-not%20run-lightgrey)
![tests](https://img.shields.io/badge/tests-not%20run-lightgrey)
![coverage](https://img.shields.io/badge/coverage-not%20run-lightgrey)
{% endif %}

{{cookiecutter.description}}

This service belongs to the parent uv workspace. Run `make bootstrap`
and `make check` from the workspace root. Add runtime dependencies with
`uv add --package {{cookiecutter.package_name}} <dependency>`.

Implement `main()` in `src/{{cookiecutter.package_name}}/main.py`, then run it with
`uv run --package {{cookiecutter.package_name}} python -m {{cookiecutter.package_name}}.main`.
Build the Dockerfile using the workspace root as the context, after `uv lock`.
{% endraw %}