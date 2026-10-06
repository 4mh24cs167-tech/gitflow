import base64
import os
from urllib.parse import urlparse
from fastapi import HTTPException

def get_canonical_github_url(value: str) -> tuple[str, str, str]:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise HTTPException(status_code=422, detail="Only HTTPS github.com repository URLs are supported")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(status_code=422, detail="Invalid repository URL. Credentials, query strings, and fragments are not allowed.")
    
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    path = path.strip("/")
    
    parts = path.split("/")
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="Invalid repository URL. Must be in the format https://github.com/owner/repository")
    
    owner, repo_name = parts[0], parts[1]
    canonical_url = f"https://github.com/{owner}/{repo_name}"
    return canonical_url, owner, repo_name


def git_environment(oauth_token: str | None = None, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Build a non-interactive Git environment without putting credentials in URLs."""
    env = (base_env or os.environ).copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    if oauth_token:
        credentials = base64.b64encode(f"x-access-token:{oauth_token}".encode("utf-8")).decode("ascii")
        env.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
        })
    return env
