"""Exercise the workspace's Jinja README and test-directory discovery lifecycle."""

import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from cookiecutter.main import cookiecutter

from .test_web import generate, run_just, workflow
from .test_web import project as project


@pytest.mark.parametrize(
    "base_url",
    ["https://example.github.io/MyRepo", "https://example.github.io", "https://docs.example.com"],
)
def test_binding_preserves_prose_and_supplies_future_scaffolds(project, tmp_path, base_url):
    prose = (
        "\n## Custom notes\nKeep this text exactly.\n"
        "![lint](https://example.com/custom.svg)\n"
        "![tests](https://img.shields.io/badge/example-blue) Inline prose stays.\n"
    )
    readmes = []
    templates = [project / "templates/readme/header.md.jinja"]
    for kind, group, name in (("service", "services", "api"), ("lib", "libs", "common")):
        assert generate(project, kind, name).returncode == 0
        readme = project / group / name / "README.md"
        template = project / "templates" / kind / "{{cookiecutter.package_name}}/README.md"
        for path in (readme, template):
            path.write_text(path.read_text() + prose)
        readmes.append(readme)
        templates.append(template)
        assert "not%20published" in readme.read_text()
    result = run_script(project, "bind_badges.py", "--pages-url", base_url + "/")
    assert result.returncode == 0, result.stderr
    assert not (project / ".github/pages.json").exists()
    for readme in readmes:
        member = readme.parent.relative_to(project).as_posix()
        assert_live_badges(readme.read_text(), base_url, member)
        assert_table_badges(project, base_url, member)
        assert readme.read_text().endswith(prose)
    before = {path: path.read_bytes() for path in [project / "README.md", *readmes, *templates]}
    assert run_script(project, "bind_badges.py", "--pages-url", base_url).returncode == 0
    assert all(path.read_bytes() == original for path, original in before.items())
    assert run_script(project, "codegen.py", "--check").returncode == 0

    remove_bootstrap_files(project)
    for kind, group, name in (("service", "services", "worker"), ("lib", "libs", "extra")):
        template = project / "templates" / kind
        assert_live_badges(
            (template / "{{cookiecutter.package_name}}/README.md").read_text(),
            base_url,
            group + "/{{cookiecutter.package_name}}",
        )
        # Direct Cookiecutter use must work without a workspace helper injecting the URL.
        member = Path(
            cookiecutter(
                str(template),
                no_input=True,
                output_dir=str(tmp_path / group),
                extra_context={"package_name": name},
            )
        )
        direct = (member / "README.md").read_text()
        assert_live_badges(direct, base_url, f"{group}/{name}")
        assert direct.endswith(prose)
        assert generate(project, kind, name).returncode == 0
        generated = (project / group / name / "README.md").read_text()
        assert generated.endswith(prose)
        assert_live_badges(generated, base_url, f"{group}/{name}")
        assert_table_badges(project, base_url, f"{group}/{name}")
    assert run_script(project, "codegen.py", "--check").returncode == 0
    assert all(readme.read_bytes() == before[readme] for readme in readmes)


def assert_live_badges(text, base_url, member):
    for label in ("lint", "tests", "coverage"):
        url = text.split(f"[![{label}](", 1)[1].split(")", 1)[0]
        assert parse_qs(urlsplit(url).query)["url"] == [
            f"{base_url}/reports/{member}/badges/{label}.json"
        ]
    assert text.count(f"]({base_url}/reports/{member}/)") == 3


def assert_table_badges(project, base_url, member):
    # All three badges must stay on the member's Markdown table row.
    row = next(
        line for line in (project / "README.md").read_text().splitlines() if f"]({member}/)" in line
    )
    assert_live_badges(row, base_url, member)


def remove_bootstrap_files(project):
    steps = workflow(project, "bootstrap-badges")["jobs"]["setup"]["steps"]
    binding = next(step for step in steps if step.get("id") == "bind")
    cleanup = next(line for line in binding["run"].splitlines() if line.startswith("rm "))
    subprocess.run(shlex.split(cleanup), cwd=project, check=True)
    assert not (project / "scripts/bind_badges.py").exists()
    assert not (project / ".github/workflows/bootstrap-badges.yml").exists()


def test_binding_an_empty_workspace_prepares_future_members(project):
    base_url = "https://example.github.io/empty"
    result = run_script(project, "bind_badges.py", "--pages-url", base_url)
    assert result.returncode == 0, result.stderr
    remove_bootstrap_files(project)
    assert generate(project, "lib", "first").returncode == 0
    assert_live_badges((project / "libs/first/README.md").read_text(), base_url, "libs/first")
    assert_table_badges(project, base_url, "libs/first")


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
            assert (
                f"![{label}](https://img.shields.io/badge/{label}-not%20published-lightgrey)"
                in text
            )
    assert generate(project, "service", "api").returncode == 0
    readme = project / "services/api/README.md"
    readme.write_text("# My service\n\nHand-maintained links and documentation.\n")
    before = readme.read_bytes()
    assert generate(project, "lib", "common").returncode == 0
    assert run_script(project, "codegen.py").returncode == 0
    assert readme.read_bytes() == before


def test_codegen_updates_tables_without_mutating_existing_members_or_config(project):
    assert generate(project, "service", "api").returncode == 0
    assert generate(project, "lib", "common").returncode == 0
    shutil.rmtree(project / "services/api")
    manifest = project / "pyproject.toml"
    readme = project / "README.md"
    member_readme = project / "libs/common/README.md"
    before = {path: path.read_bytes() for path in (readme, member_readme, manifest)}
    assert run_script(project, "codegen.py", "--check").returncode == 1
    assert all(path.read_bytes() == original for path, original in before.items())
    assert run_script(project, "codegen.py").returncode == 0
    assert "[api](services/api/)" not in readme.read_text()
    assert member_readme.read_bytes() == before[member_readme]
    assert manifest.read_bytes() == before[manifest]


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
    assert config["testpaths"] == ["tests"]
    for kind, group, name in (("service", "services", "api"), ("lib", "libs", "common")):
        assert generate(project, kind, name).returncode == 0
        (project / group / name / f"src/{name}/test_helpers.py").write_text(
            'raise RuntimeError("Source modules must not be collected as tests")\n'
        )
    (project / "tests/test_integration.py").write_text("def test_integration():\n    assert True\n")
    assert manifest.read_bytes() == before
    result = run_just(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("1 passed") == 3
    shutil.rmtree(project / "libs/common")
    result = run_just(project, "test")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("1 passed") == 2
    assert manifest.read_bytes() == before
