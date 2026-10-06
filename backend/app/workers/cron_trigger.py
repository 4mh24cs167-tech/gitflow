"""Call the authenticated polling endpoint from Render's scheduled cron service."""

import os
import sys
from urllib.parse import urlparse

import httpx


def main() -> int:
    api_url = os.environ.get("GITFLOW_API_URL", "").strip().rstrip("/")
    cron_secret = os.environ.get("GITFLOW_CRON_SECRET", "").strip()

    parsed_url = urlparse(api_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        print("GITFLOW_API_URL must be a valid HTTPS service URL.", file=sys.stderr)
        return 2
    if not cron_secret:
        print("GITFLOW_CRON_SECRET is not configured.", file=sys.stderr)
        return 2

    try:
        response = httpx.post(
            f"{api_url}/admin/polling/run",
            headers={"Authorization": f"Bearer {cron_secret}"},
            timeout=httpx.Timeout(270.0, connect=10.0),
        )
    except httpx.HTTPError:
        print("Could not reach the Gitflow polling service; check service health and network logs.", file=sys.stderr)
        return 1

    try:
        summary = response.json()
    except ValueError:
        summary = {}

    status = summary.get("status") if isinstance(summary, dict) else None
    if response.status_code >= 400:
        print(f"Polling failed with HTTP {response.status_code} (status: {status or 'unknown'}); check API logs.", file=sys.stderr)
        return 1

    if status == "skipped":
        print("Polling skipped because another run already holds the polling lock.")
        return 0

    errors = summary.get("errors", 0) if isinstance(summary, dict) else 0
    if status != "completed" or errors:
        print(f"Polling did not complete cleanly (status: {status or 'unknown'}); check API logs.", file=sys.stderr)
        return 1

    print(
        "Polling completed: "
        f"repositories={summary.get('repositories_checked', 0)}, "
        f"changed={summary.get('repositories_changed', 0)}, "
        f"commits={summary.get('commits_discovered', 0)}, "
        f"queued={summary.get('commits_queued', 0)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
