"""Exercise the workspace's Jinja README and test-directory discovery lifecycle."""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from cookiecutter.main import cookiecutter

from .test_web import generate, run_make
from .test_web import project as project


@pytest.mark.parametrize(
    "repository, base_url",
    [
        ("Example/MyRepo", "https://example.github.io/MyRepo"),
        ("Example/example.github.io", "https://example.github.io"),
    ],
)
def test_member_and_workspace_badges_derive_the_same_github_pages_url(
    project, repository, base_url
):
    manifest = project / "pyproject.toml"
    manifest.write_text(manifest.read_text().replace("example/web-example", repository))
    assert generate(project, "lib", "common").returncode == 0
    expected = f"{base_url}/reports/libs/common/badges/coverage.json"
    for path in (project / "README.md", project / "libs/common/README.md"):
        url = path.read_text().split("[![coverage](", 1)[1].split(")", 1)[0]
        assert parse_qs(urlsplit(url).query)["url"] == [expected]


def run_script(project, script, *args):
    return subprocess.run(
        [sys.executable, str(project / "scripts" / script), *args],
        cwd=project.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_readme_is_generated_from_jinja_with_an_included_header(project):
    template = project / "templates/readme/README.md.jinja"
    header = project / "templates/readme/header.md.jinja"
    assert '{% include "header.md.jinja" %}' in template.read_text()
    assert run_script(project, "codegen.py", "--check").returncode == 0
    template.write_text(template.read_text() + "\nCustom workspace documentation.\n")
    header.write_text(header.read_text().replace("## Services", "## Applications"))
    for kind, name in (("service", "zebra"), ("lib", "common"), ("service", "api")):
        result = generate(project, kind, name)
        assert result.returncode == 0, result.stderr
    readme = project / "README.md"
    text = readme.read_text()
    services, libs = text.split("## Libraries")
    assert "## Applications" in services
    assert services.index("[api](services/api/)") < services.index("[zebra](services/zebra/)")
    assert "[common](libs/common/)" in libs
    assert "[common]" not in services
    assert text.endswith("Custom workspace documentation.\n")
    assert "BEGIN GENERATED" not in text
    # A missing or hand-edited output is regenerated from the editable Jinja source.
    readme.write_text("An outdated generated README\n")
    assert run_script(project, "codegen.py", "--check").returncode == 1
    assert readme.read_text() == "An outdated generated README\n"
    readme.unlink()
    assert run_script(project, "codegen.py").returncode == 0
    assert readme.read_text() == text
    assert run_script(project, "codegen.py", "--check").returncode == 0


def test_member_templates_render_direct_links_without_a_followup_rewrite(project, tmp_path):
    for kind, group in (("service", "services"), ("lib", "libs")):
        member = cookiecutter(
            str(project / "templates" / kind),
            no_input=True,
            output_dir=str(tmp_path / group),
            extra_context={"package_name": "example"},
        )
        text = (Path(member) / "README.md").read_text()
        assert "GENERATED BADGES" not in text
        for label in ("lint", "tests", "coverage"):
            url = text.split(f"[![{label}](", 1)[1].split(")", 1)[0]
            endpoint = parse_qs(urlsplit(url).query)["url"][0]
            assert (
                endpoint
                == f"https://example.github.io/web-example/reports/{group}/example/badges/{label}.json"
            )
            assert f"](https://example.github.io/web-example/reports/{group}/example/)" in text
    assert generate(project, "service", "api").returncode == 0
    readme = project / "services/api/README.md"
    readme.write_text("# My service\n\nHand-maintained links and documentation.\n")
    before = readme.read_bytes()
    assert generate(project, "lib", "common").returncode == 0
    assert run_script(project, "codegen.py").returncode == 0
    assert readme.read_bytes() == before


def test_codegen_updates_tables_and_urls_without_mutating_existing_member_readmes(project):
    assert generate(project, "service", "api").returncode == 0
    assert generate(project, "lib", "common").returncode == 0
    shutil.rmtree(project / "services/api")
    manifest = project / "pyproject.toml"
    manifest.write_text(
        manifest.read_text().replace("example/web-example", "another/new-repository")
    )
    readme = project / "README.md"
    member_readme = project / "libs/common/README.md"
    before = {path: path.read_bytes() for path in (readme, member_readme, manifest)}
    assert run_script(project, "codegen.py", "--check").returncode == 1
    assert all(path.read_bytes() == original for path, original in before.items())
    assert run_script(project, "codegen.py").returncode == 0
    assert "[api](services/api/)" not in readme.read_text()
    assert "another.github.io/new-repository" in readme.read_text()
    assert member_readme.read_bytes() == before[member_readme]
    assert manifest.read_bytes() == before[manifest]
    # Future scaffolds take their links from the current workspace configuration.
    assert generate(project, "lib", "new_common").returncode == 0
    assert "another.github.io/new-repository" in (project / "libs/new_common/README.md").read_text()
    assert run_script(project, "codegen.py", "--check").returncode == 0


def test_bad_jinja_leaves_readme_intact_and_rolls_back_member_creation(project):
    readme = project / "README.md"
    before = readme.read_bytes()
    (project / "templates/readme/header.md.jinja").write_text("{{ missing_variable }}\n")
    result = generate(project, "lib", "common")
    assert result.returncode != 0
    assert "missing_variable" in result.stderr
    assert not (project / "libs/common").exists()
    assert not list((project / "libs").glob(".new-member-*"))
    assert readme.read_bytes() == before


def test_testpaths_discover_new_members_without_scanning_sources_or_regenerating_pyproject(project):
    manifest = project / "pyproject.toml"
    before = manifest.read_bytes()
    config = tomllib.loads(manifest.read_text())["tool"]["pytest"]["ini_options"]
    assert config["testpaths"] == ["tests", "services/*/tests", "libs/*/tests"]
    for kind, group, name in (("service", "services", "api"), ("lib", "libs", "common")):
        assert generate(project, kind, name).returncode == 0
        (project / group / name / f"src/{name}/test_helpers.py").write_text(
            'raise RuntimeError("Source modules must not be collected as tests")\n'
        )
    (project / "tests/test_integration.py").write_text("def test_integration():\n    assert True\n")
    assert manifest.read_bytes() == before
    result = run_make(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 passed" in result.stdout
    shutil.rmtree(project / "libs/common")
    result = run_make(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 passed" in result.stdout
    assert manifest.read_bytes() == before
