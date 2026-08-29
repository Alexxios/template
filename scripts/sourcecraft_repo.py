#!/usr/bin/env python3
"""Create or delete a Sourcecraft repository via the public REST API.

Usage
-----
Create a repo (prints the repo slug/id on stdout for downstream steps)::

    python scripts/sourcecraft_repo.py create \
        --org-slug "$SOURCECRAFT_ORG_SLUG" \
        --repo-slug my-test-repo \
        --visibility private

Delete a repo::

    python scripts/sourcecraft_repo.py delete \
        --org-slug "$SOURCECRAFT_ORG_SLUG" \
        --repo-slug my-test-repo

Authentication
~~~~~~~~~~~~~
The API token is read from the ``SOURCECRAFT_TOKEN`` environment variable
(a Bearer token), which is pre-defined inside Sourcecraft CI. It can be
overridden via ``SOURCECRAFT_API_TOKEN`` for local runs. The script fails
fast if no token is available.

API reference
~~~~~~~~~~~~~
* Create: POST https://api.sourcecraft.tech/orgs/{org_slug}/repos
* Delete: DELETE https://api.sourcecraft.tech/repos/{org_slug}/{repo_slug}
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API_BASE = "https://api.sourcecraft.tech"
# Sourcecraft CI injects SOURCECRAFT_TOKEN automatically; allow an override
# via SOURCECRAFT_API_TOKEN for local development.
TOKEN_ENVS = ("SOURCECRAFT_API_TOKEN", "SOURCECRAFT_TOKEN")

logger = logging.getLogger()


def _configure_logging() -> None:
    """Configure logging to write to both a file (for CI artifacts) and stderr.

    When the SOURCECRAFT_LOG_FILE environment variable is set (by CI), logs are
    written to that file *and* stderr. Otherwise, logs go to stderr only.
    CI systems may buffer stdout/stderr, so we force flush after each log record
    to ensure logs appear even if the script crashes.
    """
    log_file = os.environ.get("SOURCECRAFT_LOG_FILE", "").strip()

    def _make_handler(stream):
        handler = logging.StreamHandler(stream)
        original_emit = handler.emit
        def emit_with_flush(record):
            original_emit(record)
            handler.flush()
        handler.emit = emit_with_flush
        return handler

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Always log to stderr for immediate visibility.
    root_logger.addHandler(_make_handler(sys.stderr))

    # When running under CI, also write to the artifact file so the runner
    # can attach it to the job report.
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as fh:
            root_logger.addHandler(_make_handler(fh))
        logger.debug("logging to artifact file %s", log_file)


def _require_token() -> str:
    for env in TOKEN_ENVS:
        token = os.environ.get(env, "").strip()
        if token:
            logger.debug("using API token from %s", env)
            return token
    logger.error("no API token found in %s; set one to perform repository operations", "/".join(TOKEN_ENVS))
    sys.exit(1)


def _request(
    method: str,
    url: str,
    token: str,
    *,
    payload: dict[str, Any] | None = None,
    accept: int = 200,
) -> tuple[int, dict[str, Any] | str]:
    """Perform an HTTP request and return (status, parsed_body)."""
    logger.info("%s %s (expecting HTTP %d)", method, url, accept)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        logger.debug("request payload: %s", json.dumps(payload))

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8")
        logger.warning("HTTP %d from %s %s", status, method, url)
    except urllib.error.URLError as exc:
        logger.error("network failure contacting Sourcecraft API: %s", exc.reason)
        sys.exit(1)

    parsed: dict[str, Any] | str
    if not body:
        parsed = ""
    else:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body

    if status != accept:
        message = parsed if isinstance(parsed, str) else json.dumps(parsed, indent=2)
        logger.error("%s %s returned HTTP %d (expected %d):\n%s", method, url, status, accept, message)
        sys.exit(1)
    logger.info("%s %s -> HTTP %d OK", method, url, status)
    return status, parsed


def cmd_create(args: argparse.Namespace) -> None:
    token = _require_token()
    url = f"{API_BASE}/orgs/{args.org_slug}/repos"
    payload: dict[str, Any] = {
        "slug": args.repo_slug,
        "name": args.name or args.repo_slug,
        "visibility": args.visibility,
    }
    if args.description:
        payload["description"] = args.description
    if args.default_branch:
        payload["init_settings"] = {
            "default_branch": args.default_branch,
            "create_readme": args.create_readme,
        }

    logger.info(
        "creating repository slug=%s org=%s visibility=%s",
        args.repo_slug, args.org_slug, args.visibility,
    )
    status, body = _request("POST", url, token, payload=payload, accept=201)
    assert isinstance(body, dict)
    repo_id = body.get("id", "<unknown>")
    repo_slug = body.get("slug", args.repo_slug)
    web_url = body.get("web_url", "")
    logger.info("created repository %s (id=%s)", repo_slug, repo_id)
    if web_url:
        logger.info("web_url: %s", web_url)

    # Emit a machine-readable line for downstream CI steps.
    print(f"::set-output name=repo_id::{repo_id}")
    print(f"::set-output name=repo_slug::{repo_slug}")


def cmd_delete(args: argparse.Namespace) -> None:
    token = _require_token()
    url = f"{API_BASE}/repos/{args.org_slug}/{args.repo_slug}"
    logger.info("deleting repository slug=%s org=%s", args.repo_slug, args.org_slug)
    status, body = _request("DELETE", url, token, accept=204)
    logger.info("deleted repository %s from org %s", args.repo_slug, args.org_slug)


def _discover_latest_run(token: str, org_slug: str, repo_slug: str) -> str:
    """Discover the slug of the latest CI/CD run via the ListRuns API."""
    list_url = f"{API_BASE}/repos/{org_slug}/{repo_slug}/cicd/runs"
    logger.info("discovering latest run via %s", list_url)
    _, list_body = _request("GET", list_url, token, accept=200)
    assert isinstance(list_body, dict)
    runs = list_body.get("runs", [])
    if not runs:
        logger.error("no CI runs found for %s/%s", org_slug, repo_slug)
        sys.exit(1)
    # The API returns runs sorted by creation time (newest first).
    run_slug = runs[0]["slug"]
    logger.info("discovered latest run: slug=%s", run_slug)
    return run_slug


def _download(url: str, dest: str, token: str | None = None) -> None:
    """Download a binary blob from ``url`` to a local file ``dest``."""
    logger.info("downloading %s -> %s", url, dest)
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
    except urllib.error.HTTPError as exc:
        logger.error("HTTP %d downloading %s", exc.code, url)
        sys.exit(1)
    except urllib.error.URLError as exc:
        logger.error("network failure downloading %s: %s", url, exc.reason)
        sys.exit(1)
    logger.info("downloaded %s", dest)


def cmd_cicd_wait(args: argparse.Namespace) -> None:
    """Poll a CI/CD run until it reaches a terminal status.

    If --run-slug is not provided, the latest run is discovered via the
    ListRuns API (GET /repos/{org}/{repo}/cicd/runs).
    """
    token = _require_token()
    terminal_statuses = {"success", "failed", "canceled", "timeout"}

    # Resolve run slug: use explicit value or discover the latest run.
    run_slug: str
    if args.run_slug:
        run_slug = args.run_slug
    else:
        run_slug = _discover_latest_run(token, args.org_slug, args.repo_slug)

    url = f"{API_BASE}/repos/{args.org_slug}/{args.repo_slug}/cicd/runs/{run_slug}"

    logger.info(
        "waiting for run %s on %s/%s (interval=%ds, max_attempts=%d)",
        run_slug, args.org_slug, args.repo_slug,
        args.polling_interval, args.max_attempts,
    )

    for attempt in range(1, args.max_attempts + 1):
        _, body = _request("GET", url, token, accept=200)
        assert isinstance(body, dict)
        status = body.get("status", "<unknown>")
        logger.debug("poll #%d: status=%s", attempt, status)

        if status in terminal_statuses:
            logger.info("run reached terminal status: %s", status)
            if status == "success":
                print(f"::set-output name=final_status::{status}")
                return
            # Failed, canceled, or timed out.
            error_messages = body.get("error_messages", [])
            if error_messages:
                logger.error("run error messages: %s", error_messages)
            print(f"::set-output name=final_status::{status}")
            logger.error("run did not succeed (status=%s)", status)
            sys.exit(1)

        if attempt == args.max_attempts:
            logger.error("exceeded max attempts (%d) without reaching terminal status (last: %s)", args.max_attempts, status)
            sys.exit(1)

        logger.debug("waiting %ds before next poll...", args.polling_interval)
        time.sleep(args.polling_interval)


def cmd_cicd_artifacts(args: argparse.Namespace) -> None:
    """Download artifacts produced by a cube in a CI/CD run.

    Uses the GetCubeArtifacts API
    (GET /repos/{org}/{repo}/cicd/artifacts/{run}/{workflow}/{task}/{cube})
    to list artifacts, then downloads each one via its temporary ``download_url``
    into the local ``--output-dir`` directory.

    Artifacts are not necessarily ready the instant a run finishes: each
    artifact has a ``status`` that transitions from ``registered`` to a
    terminal value (``success``, ``failed`` or ``missing``). The
    ``download_url`` is only populated once the artifact has been obtained by
    the platform (it is a temporary URL valid for a short time after
    acquisition). This command therefore polls the endpoint until every
    artifact reaches a terminal status, then downloads the ones that
    succeeded. It fails loudly if any artifact ends up ``failed``/``missing``
    or if polling times out before all artifacts are ready.

    If --run-slug is not provided, the latest run is discovered via the
    ListRuns API (GET /repos/{org}/{repo}/cicd/runs).
    """
    token = _require_token()

    # Resolve run slug: use explicit value or discover the latest run.
    run_slug: str
    if args.run_slug:
        run_slug = args.run_slug
    else:
        run_slug = _discover_latest_run(token, args.org_slug, args.repo_slug)

    url = (
        f"{API_BASE}/repos/{args.org_slug}/{args.repo_slug}/cicd/artifacts/"
        f"{run_slug}/{args.workflow_slug}/{args.task_slug}/{args.cube_slug}"
    )
    logger.info(
        "fetching artifacts for run=%s workflow=%s task=%s cube=%s",
        run_slug, args.workflow_slug, args.task_slug, args.cube_slug,
    )

    # Artifact statuses: "registered" (pending) -> "success" | "failed" | "missing".
    terminal_statuses = {"success", "failed", "missing"}

    artifacts: list[dict[str, Any]] = []
    for attempt in range(1, args.max_attempts + 1):
        _, body = _request("GET", url, token, accept=200)
        assert isinstance(body, dict)
        artifacts = body.get("artifacts", [])
        if not artifacts:
            logger.warning("no artifacts found for cube %s in run %s", args.cube_slug, run_slug)
            return

        pending = [a for a in artifacts if a.get("status", "registered") not in terminal_statuses]
        logger.debug(
            "poll #%d: %d artifact(s), %d still pending",
            attempt, len(artifacts), len(pending),
        )
        if not pending:
            break

        if attempt == args.max_attempts:
            pending_paths = ", ".join(a.get("local_path", a.get("id", "?")) for a in pending)
            logger.error(
                "artifacts not ready after %d attempts (still pending: %s)",
                args.max_attempts, pending_paths,
            )
            sys.exit(1)

        logger.debug("waiting %ds before next poll...", args.polling_interval)
        time.sleep(args.polling_interval)
    else:
        # Loop exhausted without break: should not happen, but guard anyway.
        logger.error("exceeded max attempts (%d) waiting for artifacts", args.max_attempts)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    logger.info("found %d artifact(s)", len(artifacts))

    failed: list[str] = []
    downloaded = 0
    for art in artifacts:
        local_path = art.get("local_path", "")
        status = art.get("status", "registered")
        download_url = art.get("download_url", "")

        if status != "success":
            # Terminal but not downloadable: record and fail afterwards so the
            # user sees every broken artifact in a single run.
            failed.append(local_path or art.get("id", "<unknown>"))
            logger.error("artifact %r has terminal status %r", local_path, status)
            continue

        if not download_url:
            # Defensive: status=success must carry a download_url. If it does
            # not, the API contract was violated — fail loudly instead of
            # silently skipping.
            failed.append(local_path or art.get("id", "<unknown>"))
            logger.error("artifact %r has status=success but no download_url", local_path)
            continue

        # Preserve the artifact's declared local_path under the output dir so
        # that directory trees (e.g. a served Allure report) are reconstructed
        # faithfully. Fall back to the artifact id when local_path is empty.
        rel = local_path or art.get("id", "artifact")
        dest = os.path.join(args.output_dir, rel)
        os.makedirs(os.path.dirname(dest) or args.output_dir, exist_ok=True)
        _download(download_url, dest, token=token)
        downloaded += 1

    if failed:
        logger.error("failed to obtain %d artifact(s): %s", len(failed), ", ".join(failed))
        sys.exit(1)

    if downloaded == 0:
        logger.warning("no artifacts were downloaded for cube %s in run %s", args.cube_slug, run_slug)

    logger.info("artifacts downloaded to %s", args.output_dir)
    print(f"::set-output name=artifacts_dir::{args.output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or delete a Sourcecraft repository via the REST API."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common_org = dict(dest="org_slug", help="Organization slug")

    p_create = sub.add_parser("create", help="Create a new repository.")
    p_create.add_argument("--org-slug", **common_org, required=True)
    p_create.add_argument(
        "--repo-slug", required=True, help="Slug (and default name) of the new repo."
    )
    p_create.add_argument(
        "--name", default=None, help="Display name (defaults to --repo-slug)."
    )
    p_create.add_argument(
        "--description", default=None, help="Optional repository description."
    )
    p_create.add_argument(
        "--visibility",
        default="private",
        choices=["public", "internal", "private"],
        help="Repository visibility (default: private).",
    )
    p_create.add_argument(
        "--default-branch",
        default=None,
        help="Initialize the repo with this default branch.",
    )
    p_create.add_argument(
        "--create-readme",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create an initial README when initializing (default: true).",
    )
    p_create.set_defaults(func=cmd_create)

    p_delete = sub.add_parser("delete", help="Delete an existing repository.")
    p_delete.add_argument("--org-slug", **common_org, required=True)
    p_delete.add_argument(
        "--repo-slug", required=True, help="Slug of the repository to delete."
    )
    p_delete.set_defaults(func=cmd_delete)

    # --- cicd-wait ---
    p_wait = sub.add_parser("cicd-wait", help="Wait for a CI/CD run to reach a terminal status.")
    p_wait.add_argument("--org-slug", **common_org, required=True)
    p_wait.add_argument(
        "--repo-slug", required=True, help="Slug of the repository."
    )
    p_wait.add_argument(
        "--run-slug", default=None,
        help="Slug of the CI run to wait for (default: discover the latest run).",
    )
    p_wait.add_argument(
        "--polling-interval", type=int, default=15,
        help="Seconds between polls (default: 15).",
    )
    p_wait.add_argument(
        "--max-attempts", type=int, default=120,
        help="Maximum number of polls before giving up (default: 120 = 30 min).",
    )
    p_wait.set_defaults(func=cmd_cicd_wait)

    # --- cicd-artifacts ---
    p_art = sub.add_parser(
        "cicd-artifacts",
        help="Download artifacts produced by a cube in a CI/CD run.",
    )
    p_art.add_argument("--org-slug", **common_org, required=True)
    p_art.add_argument(
        "--repo-slug", required=True, help="Slug of the repository."
    )
    p_art.add_argument(
        "--run-slug", default=None,
        help="Slug of the CI run (default: discover the latest run).",
    )
    p_art.add_argument(
        "--workflow-slug", required=True,
        help="Workflow name as defined in the CI config.",
    )
    p_art.add_argument(
        "--task-slug", required=True,
        help="Task name as defined in the CI config.",
    )
    p_art.add_argument(
        "--cube-slug", required=True,
        help="Cube name as defined in the CI config.",
    )
    p_art.add_argument(
        "--output-dir", default="artifacts",
        help="Local directory to download artifacts into (default: artifacts).",
    )
    p_art.add_argument(
        "--polling-interval", type=int, default=15,
        help="Seconds between polls while waiting for artifacts to become ready (default: 15).",
    )
    p_art.add_argument(
        "--max-attempts", type=int, default=40,
        help="Maximum number of polls before giving up (default: 40 = 10 min).",
    )
    p_art.set_defaults(func=cmd_cicd_artifacts)

    return parser


def main(argv: list[str] | None = None) -> None:
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    logger.debug("parsed args: %s", args)
    args.func(args)


if __name__ == "__main__":
    main()
