{% raw %}# {{cookiecutter.package_name}}

{% set owner, repository = cookiecutter.github_repository.split("/") -%}
{% set pages_url = "https://" ~ owner.lower() ~ ".github.io" ~ ("" if repository.lower() == owner.lower() ~ ".github.io" else "/" ~ repository) -%}
{% set member_url = pages_url ~ "/reports/libs/" ~ cookiecutter.package_name -%}
[![lint](https://img.shields.io/endpoint?url={{ (member_url ~ "/badges/lint.json") | urlencode }})]({{member_url}}/)
[![tests](https://img.shields.io/endpoint?url={{ (member_url ~ "/badges/tests.json") | urlencode }})]({{member_url}}/)
[![coverage](https://img.shields.io/endpoint?url={{ (member_url ~ "/badges/coverage.json") | urlencode }})]({{member_url}}/)

{{cookiecutter.description}}

This library belongs to the parent uv workspace. Run `make bootstrap`
and `make check` from the workspace root. Add runtime dependencies with
`uv add --package {{cookiecutter.package_name}} <dependency>`.
{% endraw %}