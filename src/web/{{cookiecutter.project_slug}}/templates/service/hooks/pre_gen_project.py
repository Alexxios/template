{% raw %}"""Validate package and Kubernetes names before rendering the service."""

import keyword
import re

name = {{ cookiecutter.package_name | tojson }}
if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
    raise SystemExit("Use a lowercase Python package name, such as billing_api.")

kubernetes_name = {{ cookiecutter.kubernetes_name | tojson }}
if not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", kubernetes_name):
    raise SystemExit(
        "Use a Kubernetes name of at most 63 lowercase letters, digits, or hyphens, "
        "starting with a letter and ending with a letter or digit. "
        "The default replaces underscores in the package name with hyphens; "
        "customize kubernetes_name in templates/service/cookiecutter.json if needed."
    )
{% endraw %}
