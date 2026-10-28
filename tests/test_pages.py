"""Exercise cross-run artifact selection and a real combined MkDocs build."""

import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import pytest
import yaml
from mkdocs.commands.build import build
from mkdocs.config import load_config

from scripts import build_pages
from scripts.new_template import create_template

ROOT = Path(__file__).resolve().parents[1]


def artifact(run_id, *, branch="main", expired=False):
    return {
        "id": run_id,
        "name": "generated-base-ci",
        "expired": expired,
        "workflow_run": {"id": run_id, "head_branch": branch},
    }


def run(run_id, **overrides):
    return {
        "id": run_id,
        "status": "completed",
        "event": "push",
        "head_branch": "main",
        "head_repository": {"full_name": "example/collection"},
        "path": ".github/workflows/validate-base.yml",
        "head_sha": "a" * 40,
        "html_url": f"https://github.com/example/collection/actions/runs/{run_id}",
        "conclusion": "success",
        **overrides,
    }


def test_fetch_skips_untrusted_expired_and_incomplete_sites(tmp_path, monkeypatch):
    runs = {
        9: run(9, event="pull_request"),
        7: run(7, head_repository={"full_name": "fork/collection"}),
        6: run(6, status="in_progress"),
        5: run(5, path=".github/workflows/other.yml"),
        4: run(4),  # An older bundle with reports only.
        3: run(3, conclusion="failure"),  # Docs are valid even though tests failed.
    }
    artifacts = [artifact(i) for i in range(9, 1, -1)]
    artifacts.insert(0, artifact(10, expired=True))
    artifacts[2] = artifact(8, branch="feature")

    def api(endpoint):
        if "/artifacts?" in endpoint:
            return {"artifacts": artifacts, "total_count": len(artifacts)}
        return runs[int(endpoint.rsplit("/", 1)[1])]

    downloads = []

    def download(command, **kwargs):
        run_id = int(command[3])
        downloads.append(run_id)
        directory = Path(command[-1]) / ("reports" if run_id == 4 else "docs")
        directory.mkdir()
        (directory / "index.html").write_text(f"Site from {run_id}")

    monkeypatch.setattr(build_pages, "github_json", api)
    monkeypatch.setattr(build_pages.subprocess, "run", download)
    destination = tmp_path / "base"
    source = build_pages.fetch_template("example/collection", "main", "base", destination)
    assert downloads == [4, 3]
    assert source["run_id"] == 3
    assert source["conclusion"] == "failure"
    assert (destination / "docs/index.html").read_text() == "Site from 3"
    assert not (destination / "reports").exists()
    assert json.loads((destination / "source.json").read_text()) == source


def test_fetch_paginates_and_accepts_default_branch_manual_runs(tmp_path, monkeypatch):
    pages = []

    def api(endpoint):
        if "/artifacts?" not in endpoint:
            return run(1, event="workflow_dispatch")
        page = int(parse_qs(urlsplit(endpoint).query)["page"][0])
        pages.append(page)
        return {
            "artifacts": [artifact(i, expired=True) for i in range(101, 1, -1)]
            if page == 1
            else [artifact(1)],
            "total_count": 101,
        }

    def download(command, **kwargs):
        docs = Path(command[-1]) / "docs"
        docs.mkdir()
        (docs / "index.html").write_text("Manual build")

    monkeypatch.setattr(build_pages, "github_json", api)
    monkeypatch.setattr(build_pages.subprocess, "run", download)
    assert build_pages.fetch_template("example/collection", "main", "base", tmp_path / "base")
    assert pages == [1, 2]


def test_fetch_missing_artifacts_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(build_pages, "github_json", lambda _: {"artifacts": [], "total_count": 0})
    assert (
        build_pages.fetch_template("example/collection", "main", "base", tmp_path / "base") is None
    )
    assert not (tmp_path / "base").exists()


def test_late_older_run_cannot_replace_newer_documentation(tmp_path, monkeypatch):
    def api(endpoint):
        if "/artifacts?" in endpoint:
            return {
                "artifacts": [{**artifact(1), "id": 100}, {**artifact(2), "id": 99}],
                "total_count": 2,
            }
        return run(int(endpoint.rsplit("/", 1)[1]))

    def download(command, **kwargs):
        docs = Path(command[-1]) / "docs"
        docs.mkdir()
        (docs / "index.html").write_text(f"Run {command[3]}")

    monkeypatch.setattr(build_pages, "github_json", api)
    monkeypatch.setattr(build_pages.subprocess, "run", download)
    source = build_pages.fetch_template("example/collection", "main", "base", tmp_path / "base")
    assert source["run_id"] == 2
    assert (tmp_path / "base/docs/index.html").read_text() == "Run 2"


@pytest.mark.parametrize("failure", ["api", "download", "symlink"])
def test_fetch_failures_do_not_publish_partial_downloads(tmp_path, monkeypatch, failure):
    def api(endpoint):
        if failure == "api":
            raise subprocess.CalledProcessError(1, "gh api")
        if "/artifacts?" in endpoint:
            return {"artifacts": [artifact(1)], "total_count": 1}
        return run(1)

    def download(command, **kwargs):
        docs = Path(command[-1]) / "docs"
        docs.mkdir()
        (docs / "index.html").write_text("Partial site")
        if failure == "download":
            raise subprocess.CalledProcessError(1, command)
        (docs / "outside").symlink_to(tmp_path)

    monkeypatch.setattr(build_pages, "github_json", api)
    monkeypatch.setattr(build_pages.subprocess, "run", download)
    with pytest.raises((subprocess.CalledProcessError, ValueError)):
        build_pages.fetch_template("example/collection", "main", "base", tmp_path / "base")
    assert not (tmp_path / "base").exists()


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.urls.append(value)


def test_combined_build_preserves_sites_assets_search_reports_and_project_urls(tmp_path):
    artifacts = tmp_path / "artifacts"
    for name in ("base", "web"):
        project = tmp_path / name
        (project / "docs").mkdir(parents=True)
        (project / "mkdocs.yml").write_text(f"site_name: Example {name}\n")
        (project / "docs/index.md").write_text(f"# {name} docs\n\n[Guide](guide.md)\n")
        (project / "docs/guide.md").write_text(f"# {name} guide\n\n![Logo](logo.svg)\n")
        (project / "docs/logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        bundle = artifacts / name
        build(load_config(str(project / "mkdocs.yml"), strict=True, site_dir=str(bundle / "docs")))
        (bundle / "reports").mkdir()
        (bundle / "reports/index.html").write_text('<a href="coverage/">Coverage</a>')
        (bundle / "reports/coverage").mkdir()
        (bundle / "reports/coverage/index.html").write_text("Coverage")
        (bundle / "source.json").write_text(
            json.dumps(
                {
                    "run_id": 123,
                    "commit": "a" * 40,
                    "conclusion": "success",
                    "url": "https://github.com/example/collection/actions/runs/123",
                }
            )
        )

    output = tmp_path / "site"
    build_pages.build_site(artifacts, output, site_url="https://example.github.io/collection")
    assert "Python Template Collection" in (output / "index.html").read_text()
    assert (output / "search/search_index.json").is_file()
    catalog = (output / "generated/index.html").read_text()
    assert "aaaaaaaaaaaa" in catalog
    for name in ("base", "web"):
        for path in (artifacts / name / "docs").rglob("*"):
            if path.is_file():
                copied = output / "templates" / name / path.relative_to(artifacts / name / "docs")
                assert copied.read_bytes() == path.read_bytes()
        assert (output / "templates" / name / "ci/coverage/index.html").read_text() == "Coverage"
    urls = [
        urljoin("https://example.github.io/collection/generated/", link)
        for link in Links(catalog).urls
    ]
    for name in ("base", "web"):
        assert f"https://example.github.io/collection/templates/{name}/" in urls
        assert f"https://example.github.io/collection/templates/{name}/ci/" in urls
    assert set(json.loads((output / "template-sources.json").read_text())) == {"base", "web"}

    # Rebuilding cleans removed templates and never requires an artifact for a new template.
    shutil.rmtree(artifacts / "web")
    build_pages.build_site(artifacts, output)
    assert not (output / "templates/web").exists()
    assert (output / "templates/base/index.html").is_file()
    assert "Documentation is not available yet." in (output / "generated/index.html").read_text()


def test_new_templates_join_the_single_publisher(collection):
    create_template("python-lib", root=collection)
    workflow = yaml.load(
        (collection / ".github/workflows/pages.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert workflow["on"]["workflow_run"]["workflows"] == [
        "Check metatemplate",
        "Validate python-lib",
    ]
    assert workflow["concurrency"]["group"] == "github-pages"
    guard = workflow["jobs"]["build"]["if"]
    assert "github.event.repository.default_branch" in guard
    assert "head_repository.full_name == github.repository" in guard
    assert '["push", "workflow_dispatch"]' in guard
    for path in (collection / ".github/workflows").glob("validate-*.yml"):
        assert "actions/deploy-pages" not in path.read_text()
