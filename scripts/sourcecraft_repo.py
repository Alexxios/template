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

    return parser


def main(argv: list[str] | None = None) -> None:
    _configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    logger.debug("parsed args: %s", args)
    args.func(args)


if __name__ == "__main__":
    main()
