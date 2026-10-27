# GitHub Pages reports

This template supports GitHub Actions. Set `github_repository=owner/repository`
when creating the workspace. README badge URLs are derived from this value and
stored repository metadata in `tool.codegen.github_repository`; there is no
separate reports URL setting. Select **GitHub Actions** as the repository's
Pages source once. The default site is `https://owner.github.io/repository/`
(or `https://owner.github.io/` for an `owner.github.io` repository).

## Published layout

```text
/
├── index.html                         MkDocs documentation
├── ci-reports/                        This guide
└── reports/
    ├── index.html                     Service/library status table
    ├── allure/index.html              Workspace Allure report and trends
    ├── history.jsonl                  Allure 3 history
    ├── allure-results/                Raw Allure results and attachments
    ├── coverage/                      Workspace source coverage
    ├── junit.xml                      Workspace test results
    ├── coverage.xml, coverage.json    Workspace coverage data
    ├── ruff.json, ruff-format.json    Native lint and formatting findings
    ├── services/<name>/
    │   ├── index.html                 Only this service's results
    │   ├── badges/
    │   │   ├── lint.json              Shields endpoint
    │   │   ├── tests.json             Shields endpoint
    │   │   └── coverage.json          Shields endpoint
    │   ├── coverage/                  Only this service's source coverage
    │   └── summary.json, lint.json, junit.xml, coverage.json
    └── libs/<name>/                   Same layout, only this library's results
```

The site is deployed using an Actions Pages artifact; a `gh-pages` Git branch
is not required. Pull requests retain `check-reports` artifacts without deploying.

## Badge scope

Every member README and its row in the workspace README use the same three
Shields endpoints under that member's report directory. Clicking any badge opens
that member's report, which includes a link to its own coverage source listing.

- **Lint:** Ruff diagnostics and formatting violations beneath that member's
  directory, including its tests.
- **Tests:** passed, failed, and skipped test cases from that member's `tests/`
  directory. Root integration tests are kept in the workspace report.
- **Coverage:** covered lines and branches divided by total executable lines and
  branches under that member's `src/`. Execution by integration tests contributes
  to coverage of that source; other members' source never enters the denominator.

Missing or interrupted results show `unavailable` or `no data`; empty and skipped
test suites do not show a passing test badge. Source coverage pages exist when
coverage data is available. Failed tests and lint still produce reports and a
deployment when report generation and documentation succeed. The workflow remains
failed when a check fails. Shields needs public access to the endpoint JSON.

## Allure history

Default-branch CI restores `reports/history.jsonl` from a branch-specific Actions
cache, builds Allure, and saves the updated history under a unique run/attempt
key. A failed test run still enters history when Allure generation succeeds.
Runs are serialized to avoid competing history updates. Cache eviction starts a
new history. This follows the base template's Allure 3 history flow.

Pull requests generate their own Allure report without restoring, appending, or
saving default-branch history. The Allure report is workspace-wide; member badges
come from the separately filtered member reports.

`make lint` and `make test` remain direct Ruff/pytest commands. CI captures native
JSON/XML outputs and runs `scripts/build_reports.py` afterward to render member
pages and badge JSON. That script does not execute or replace the checks.
