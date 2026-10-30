"""Build the collection's MkDocs site with documentation fetched from validation runs."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- GENERATED TEMPLATE SITES -->"


def template_names(root: Path) -> list[str]:
    return sorted(path.parent.name for path in (root / "src").glob("*/cookiecutter.json"))


def github_json(endpoint: str) -> dict:
    result = subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def reports_path(root: Path, name: str) -> PurePosixPath:
    """Locate the report entry point within a template's collected CI site."""
    config = root / "tests" / name.replace("-", "_") / "validation.toml"
    path = PurePosixPath(tomllib.loads(config.read_text())["github"].get("reports_path", "."))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{config}: github.reports_path must stay within the collected CI site")
    return path


def fetch_template(repository: str, branch: str, name: str, destination: Path) -> dict | None:
    """Find the newest retained docs from this template's trusted default-branch CI.

    Runs that failed tests may still have complete documentation. Expired artifacts,
    PRs, other branches, and old bundles without docs must not replace a usable site.
    API and download errors fail the build rather than silently dropping a site.
    """
    page = 1
    artifact_name = f"generated-{name}-ci"
    candidates = []
    while True:
        query = urlencode({"name": artifact_name, "per_page": 100, "page": page})
        response = github_json(f"repos/{repository}/actions/artifacts?{query}")
        artifacts = response["artifacts"]
        for artifact in artifacts:
            if artifact["expired"] or artifact["name"] != artifact_name:
                continue
            summary = artifact.get("workflow_run") or {}
            if summary.get("head_branch") != branch:
                continue
            candidates.append(summary["id"])
        if page * 100 >= response["total_count"] or not artifacts:
            break
        page += 1
    # Order by validation run, not artifact upload: an older, slower run (or
    # rerun) can upload its bundle after a newer validation has already finished.
    for run_id in sorted(set(candidates), reverse=True):
        run = github_json(f"repos/{repository}/actions/runs/{run_id}")
        if (
            run["status"] != "completed"
            or run["event"] not in {"push", "workflow_dispatch"}
            or run["head_branch"] != branch
            or run["head_repository"]["full_name"] != repository
            or run["path"] != f".github/workflows/validate-{name}.yml"
        ):
            continue
        with tempfile.TemporaryDirectory(prefix="template-artifact-") as temporary:
            downloaded = Path(temporary)
            subprocess.run(
                [
                    "gh",
                    "run",
                    "download",
                    str(run_id),
                    "--repo",
                    repository,
                    "--name",
                    artifact_name,
                    "--dir",
                    str(downloaded),
                ],
                check=True,
            )
            index = downloaded / "docs/index.html"
            if not index.is_file() or not index.stat().st_size:
                continue
            # Pages does not support symlinks, including links outside a bundle.
            if any(path.is_symlink() for path in downloaded.rglob("*")):
                raise ValueError(f"{artifact_name} contains a symbolic link")
            shutil.copytree(downloaded, destination)
        source = {
            "run_id": run_id,
            "commit": run["head_sha"],
            "url": run["html_url"],
            "conclusion": run["conclusion"],
        }
        (destination / "source.json").write_text(json.dumps(source, indent=2) + "\n")
        return source
    return None


def build_site(artifacts: Path, output: Path, *, root: Path = ROOT, site_url: str = "") -> None:
    """Build root docs, then mount each prebuilt site without rewriting its assets."""
    from mkdocs.commands.build import build
    from mkdocs.config import load_config

    entries = []
    sources = {}
    available = []
    for name in template_names(root):
        bundle = artifacts / name
        index = bundle / "docs/index.html"
        if not index.is_file() or not index.stat().st_size:
            entries.append(f"## {name}\n\nDocumentation is not available yet.\n")
            continue
        available.append(name)
        # HTML links deliberately point to prebuilt files mounted after MkDocs.
        # Their URLs are relative to the generated/ catalog page, including on
        # project Pages URLs and custom domains.
        entry = f'## {name}\n\n<a href="../templates/{name}/">Open documentation</a>'
        report = reports_path(root, name)
        if (bundle / "reports" / report / "index.html").is_file():
            url = PurePosixPath("..", "templates", name, "ci") / report
            entry += f' · <a href="{html.escape(str(url), quote=True)}/">CI reports</a>'
        source_path = bundle / "source.json"
        if source_path.is_file():
            source = json.loads(source_path.read_text())
            sources[name] = source
            entry += (
                f"\n\n[Validation run]({source['url']}), commit `{source['commit'][:12]}` "
                f"({html.escape(source['conclusion'] or 'unknown')})."
            )
        entries.append(entry + "\n")

    with tempfile.TemporaryDirectory(prefix="collection-docs-") as temporary:
        docs = Path(temporary) / "docs"
        shutil.copytree(root / "docs", docs, ignore=shutil.ignore_patterns("sourcecraft"))
        catalog = docs / "generated.md"
        content = catalog.read_text()
        if MARKER not in content:
            raise ValueError(f"docs/generated.md must contain {MARKER}")
        catalog.write_text(content.replace(MARKER, "\n".join(entries)))
        overrides = {"site_url": site_url.rstrip("/") + "/"} if site_url else {}
        config = load_config(
            str(root / "mkdocs.yml"),
            strict=True,
            docs_dir=str(docs),
            site_dir=str(output.resolve()),
            **overrides,
        )
        build(config)

    for name in available:
        bundle = artifacts / name
        target = output / "templates" / name
        shutil.copytree(bundle / "docs", target)
        if (bundle / "reports").is_dir():
            shutil.copytree(bundle / "reports", target / "ci")
    (output / "template-sources.json").write_text(json.dumps(sources, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repository", help="GitHub owner/repository to fetch retained artifacts")
    source.add_argument(
        "--artifacts-dir", type=Path, help="Use local <template>/docs and reports bundles"
    )
    parser.add_argument("--branch", default="main", help="Repository default branch")
    parser.add_argument("--site-dir", type=Path, default=Path("site"))
    parser.add_argument(
        "--site-url", default="", help="Published Pages URL, including the repository path"
    )
    args = parser.parse_args()
    if args.artifacts_dir:
        build_site(args.artifacts_dir, args.site_dir, site_url=args.site_url)
        return
    with tempfile.TemporaryDirectory(prefix="generated-sites-") as temporary:
        artifacts = Path(temporary)
        for name in template_names(ROOT):
            source = fetch_template(args.repository, args.branch, name, artifacts / name)
            if source is None:
                print(
                    f"::warning::No retained documentation for {name}; run Validate {name} on {args.branch}."
                )
        build_site(artifacts, args.site_dir, site_url=args.site_url)


if __name__ == "__main__":
    main()
