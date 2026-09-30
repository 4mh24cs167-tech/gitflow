with open("backend/app/api/routes/webhooks.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"repo_url = payload\.get\(\"repository\", \{\}\)\.get\(\"clone_url\"\)\s+commit_sha = payload\.get\(\"after\"\)",
    """repo_url = payload.get("repository", {}).get("clone_url") or payload.get("repository", {}).get("html_url")
        commit_sha = payload.get("after")
        try:
            canonical_url, _, _ = get_canonical_github_url(repo_url)
        except Exception:
            canonical_url = repo_url""",
    content
)

with open("backend/app/api/routes/webhooks.py", "w", encoding="utf-8") as f:
    f.write(content)
