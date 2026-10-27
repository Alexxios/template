# CI and GitHub Pages reports

## Checks

`checks.yml` is shared by default-branch and pull-request workflows. It discovers
`services/*/pyproject.toml` and `libs/*/pyproject.toml` for a dynamic job matrix,
including an independent `integration` job even when there are no members.
`fail-fast: false` lets healthy members finish when another fails collection.
A separate tooling job checks the generated README and builds documentation.

Pants owns the dependency graph and CI target selection. Each member scaffold
includes a `BUILD` file covering its Python sources, tests, and other files.
Pants infers first-party dependencies from Python imports. uv continues to own
package installation and its lockfile; Just runs the existing lint/test commands.
For runtime relationships that cannot be inferred from imports, add an explicit
dependency such as `libs/common:member` to the consumer's `python_sources` target
in its `BUILD` file. Manifest declarations alone do not create Pants graph edges.

PR discovery runs `pants --changed-since=<merge-base> --changed-dependents=transitive list`
and converts its target addresses into unique member paths with `jq`. Integration
always runs. Member metadata/assets are dependencies of that member's Python
targets; shared configuration, lockfiles, and tooling are dependencies of all
members. Deletions and renames run the full matrix because a removed import may
no longer have an owner in the current graph. Default-branch publication also
checks every member, keeping published reports and Allure history complete.

Install the [Pants launcher](https://www.pantsbuild.org/stable/docs/getting-started/installing-pants)
for local queries; `pants.toml` pins the engine version. CI installs it in discovery.
There is no generated dependency graph or dependency regeneration command:

```bash
pants dependencies --transitive services/api:member
pants dependents --transitive libs/common::
pants --changed-since=HEAD --changed-dependents=transitive list
```

See [Pants target selection](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection)
for native filters and changed-file options. PRs build Allure reports for selected
scopes only; unselected members have unavailable results in the combined artifact.

The same Just commands run locally and in CI:

```bash
just check services/api
just test libs/common
just lint integration
just check
just reports
```

Each member's pytest invocation runs from its directory, installs its declared
workspace/runtime dependencies and shared dev tools into `.venvs/<group>/<name>`,
and measures only its own `src/`. The shared uv lockfile still resolves the whole
workspace. Separate environments expose imports of unrelated workspace packages;
they do not prevent access to transitive or tooling dependencies.

Integration tests use a separate environment with all members installed. Their
coverage does not contribute to member badges. Empty integration suites are
allowed; empty member suites fail. Root scripts and integration tests are linted
under the integration scope. Members run their own lint and formatting checks.

Native Ruff, pytest, coverage, and Allure outputs go directly to each scope's
report directory. `build_reports.py` only summarizes those outputs; it neither
runs checks nor partitions workspace-wide results. Missing results/tool errors
show unavailable, empty suites show no tests, and skipped suites show skipped.
Reports are published after failing checks when report generation succeeds;
the checks keep their failure status. PRs retain artifacts without publishing.

## One-time badge setup

Cookiecutter and local scaffolding require no repository name or URL. READMEs
initially contain neutral **not published** Shields badges.

1. Create the GitHub repository and select **GitHub Actions** as its Pages source.
2. Under Settings → Actions → General → Workflow permissions, enable **Allow
   GitHub Actions to create and approve pull requests**. Organization policy must
   permit this setting.
3. Push the project. After a successful Pages deployment, `bootstrap-badges.yml`
   reads the actual Pages URL from GitHub (including custom domains) and opens
   the `automation/bootstrap-badges` PR. If PR creation was disabled, enable it
   and rerun the failed setup workflow from Actions.
4. If the PR's checks await approval, select **Approve workflows to run**. Review
   and merge the PR. It binds badge links in existing member READMEs and in the
   service, library, and workspace README templates, then regenerates the workspace
   README. It deletes both its workflow and `scripts/bind_badges.py` in that PR.

The setup uses the built-in `GITHUB_TOKEN` with `contents: write` and
`pull-requests: write`; no custom token or secret is required. The workflow file
change is a deletion only. The PR does not create or modify workflow YAML.
GitHub can require approval before running checks on token-created PRs; see
[GitHub's workflow-triggering rules](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow).

Reruns use the same PR branch. The workflow only responds to default-branch
publication from this repository and checks that the deployment job succeeded,
even when some member checks failed. It never uses PR artifacts or code.

Future `just new-service` and `just new-lib` commands render direct links from
the bound templates without Git/network access or a saved URL configuration.
Running Cookiecutter directly on either member template works the same way.
The setup preserves member prose and updates only standalone Shields lint,
tests, and coverage badge lines. Normal codegen never rewrites member READMEs.

After a Pages/domain move, update the plain report URLs and URL-encoded Shields
endpoints in existing member READMEs, `templates/service/*/README.md`,
`templates/lib/*/README.md`, and `templates/readme/header.md.jinja`, then run
`just codegen`. Shields needs public access to the endpoint JSON.

## Published layout

```text
/
├── index.html                         MkDocs documentation
├── ci-reports/                        This guide
└── reports/
    ├── index.html                     Links and status for every scope
    ├── services/<name>/
    │   ├── index.html                 Only this service's check results
    │   ├── badges/{lint,tests,coverage}.json
    │   ├── coverage/                  Only its source, from its tests
    │   ├── allure/                    Its Allure report and trends
    │   ├── allure-results/            Native results and attachments
    │   ├── history.jsonl              Published Allure history snapshot
    │   ├── junit.xml
    │   ├── coverage.xml, coverage.json
    │   ├── ruff.json, ruff-format.json
    │   ├── lint.exit, format.exit, test.exit
    │   └── summary.json
    ├── libs/<name>/                   Same layout for each library
    └── integration/                   Separate cross-member results
```

Pages deployment uses an Actions artifact; no `gh-pages` Git branch is needed.
Coverage pages exist only when data is available. Every badge opens its own
member's report, which links to its coverage and Allure pages.

## Allure history

The reporting job restores `.allure-history/` from a default-branch cache and
builds an Allure report for each scope using a separate `<scope>.jsonl` history
file. It then saves the histories using a unique run/attempt key. Failed test
runs still enter history. Default-branch workflows are serialized to avoid
competing history updates. Cache eviction starts new history.

PRs build Allure reports without restoring or saving history. Each scope's
artifact is uploaded even if its checks fail; the reporting job collects them
into `check-reports` and, on the default branch, the Pages artifact.
