"""Bind README and template badges; deleted by the one-time setup PR."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import quote, urlsplit

from codegen import ROOT, members, sync


def bind_readme(readme: Path, pages_url: str, member_path: str) -> None:
    text = readme.read_text()
    member_url = f"{pages_url}/reports/{member_path}"
    # Encode the fixed URL prefix while leaving Jinja member placeholders renderable.
    endpoint = quote(f"{pages_url}/reports/", safe="/") + member_path
    for label in ("lint", "tests", "coverage"):
        line = (
            f"[![{label}](https://img.shields.io/endpoint?url={endpoint}/badges/{label}.json)]"
            f"({member_url}/)"
        )
        image = rf"!\[{label}\]\(https://img\.shields\.io/[^\n)]*\)"
        # Replace only standalone Shields badge lines; preserve prose and other images.
        text = re.sub(
            rf"^(?:{image}|\[{image}\]\([^\n)]*\))$",
            lambda _, line=line: line,
            text,
            flags=re.MULTILINE,
        )
    readme.write_text(text)


def bind(pages_url: str) -> None:
    url = urlsplit(pages_url)
    if url.scheme != "https" or not url.netloc or url.query or url.fragment or url.username:
        raise ValueError("Expected an HTTPS Pages base URL without credentials, query, or fragment")
    pages_url = pages_url.rstrip("/")
    for member in members():
        readme = member / "README.md"
        if readme.exists():
            bind_readme(readme, pages_url, member.relative_to(ROOT).as_posix())
    for kind, group in (("service", "services"), ("lib", "libs")):
        package = "{% raw %}{{cookiecutter.package_name}}{% endraw %}"
        bind_readme(
            ROOT / "templates" / kind / package / "README.md", pages_url, f"{group}/{package}"
        )
    bind_readme(ROOT / "templates/readme/header.md.jinja", pages_url, "{% raw %}{{ path }}{% endraw %}")
    sync()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-url", required=True)
    args = parser.parse_args()
    bind(args.pages_url)
