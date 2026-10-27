{% raw %}# {{cookiecutter.package_name}}

{% if cookiecutter.reports_url -%}
[![lint](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/libs/" ~ cookiecutter.package_name ~ "/lint.json") | urlencode }})]({{cookiecutter.reports_url}}/lint.json)
[![tests](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/libs/" ~ cookiecutter.package_name ~ "/tests.json") | urlencode }})]({{cookiecutter.reports_url}}/tests.json)
[![coverage](https://img.shields.io/endpoint?url={{ (cookiecutter.reports_url ~ "/badges/libs/" ~ cookiecutter.package_name ~ "/coverage.json") | urlencode }})]({{cookiecutter.reports_url}}/coverage/index.html)
{% else -%}
![lint](https://img.shields.io/badge/lint-not%20run-lightgrey)
![tests](https://img.shields.io/badge/tests-not%20run-lightgrey)
![coverage](https://img.shields.io/badge/coverage-not%20run-lightgrey)
{% endif %}

{{cookiecutter.description}}

This library belongs to the parent uv workspace. Run `make bootstrap`
and `make check` from the workspace root. Add runtime dependencies with
`uv add --package {{cookiecutter.package_name}} <dependency>`.
{% endraw %}