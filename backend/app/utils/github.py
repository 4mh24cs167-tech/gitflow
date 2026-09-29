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
