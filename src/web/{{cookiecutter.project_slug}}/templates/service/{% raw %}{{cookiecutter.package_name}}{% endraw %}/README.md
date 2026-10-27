{% raw %}# {{cookiecutter.package_name}}

![lint](https://img.shields.io/badge/lint-not%20published-lightgrey)
![tests](https://img.shields.io/badge/tests-not%20published-lightgrey)
![coverage](https://img.shields.io/badge/coverage-not%20published-lightgrey)

{{cookiecutter.description}}

Run `just check services/{{cookiecutter.package_name}}` from the workspace root.
Add dependencies with `uv add --package {{cookiecutter.package_name}} <dependency>`.
{% endraw %}
