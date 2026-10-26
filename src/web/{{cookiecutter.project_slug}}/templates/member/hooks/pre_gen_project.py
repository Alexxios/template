{% raw %}"""Validate package names before rendering Python imports and paths."""

import keyword
import re

name = {{ cookiecutter.package_name | tojson }}
if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
    raise SystemExit("Use a lowercase Python package name, such as billing_api.")
{% endraw %}