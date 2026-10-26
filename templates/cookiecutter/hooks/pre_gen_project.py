"""Validate the template directory name for direct Cookiecutter usage."""

import re
import sys

name = "{{cookiecutter.template_name}}"
if not re.fullmatch(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*", name):
    sys.exit("Use a lowercase template name with letters, numbers, '-' or '_'.")
