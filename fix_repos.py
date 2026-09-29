import re

with open("backend/app/api/routes/repositories.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update validate_github_url
old_val = """def validate_github_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise HTTPException(status_code=422, detail="Only HTTPS github.com repository URLs are supported")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path.endswith(".git"):
        raise HTTPException(status_code=422, detail="Invalid repository URL")
    return f"https://github.com{parsed.path}"
"""
new_val = """def validate_github_url(value: str) -> tuple[str, str, str]:
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
    # Canonical URL
    canonical_url = f"https://github.com/{owner}/{repo_name}"
    return canonical_url, owner, repo_name
"""
content = content.replace(old_val, new_val)

# 2. Update queue_scan to not require OAuth token for HEAD
old_queue = """    if sha == "head":
        # Resolve HEAD using github token
        repo = await db.execute(select(Repository).where(Repository.id == repository_id))
        repo = repo.scalars().first()
        
        plain_token = decrypt_token(current_user.github_access_token)
        if not plain_token:
            raise HTTPException(status_code=409, detail="GitHub authentication required to resolve HEAD")
            
        try:
            # Extract owner/repo from URL (e.g. https://github.com/octocat/Hello-World.git)
            path = urlparse(repo.url).path
            if path.endswith(".git"):
                path = path[:-4]
            path = path.strip("/")
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"https://api.github.com/repos/{path}/commits/HEAD",
                    headers={"Authorization": f"Bearer {plain_token}", "Accept": "application/vnd.github+json"}
                )
                response.raise_for_status()
                sha = response.json().get("sha", "").lower()
        except Exception:
            raise HTTPException(status_code=503, detail="Failed to resolve HEAD commit from GitHub")
        finally:
            del plain_token"""
new_queue = """    if sha == "head":
        repo = await db.execute(select(Repository).where(Repository.id == repository_id))
        repo = repo.scalars().first()
        
        path = urlparse(repo.url).path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        path = path.strip("/")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
                # Try anonymous fetch
                response = await client.get(
                    f"https://api.github.com/repos/{path}/commits/HEAD",
                    headers=headers
                )
                if response.status_code == 403 or response.status_code == 404:
                    # Fallback to token if rate limited and user has token
                    plain_token = decrypt_token(current_user.github_access_token) if current_user.github_access_token else None
                    if plain_token:
                        headers["Authorization"] = f"Bearer {plain_token}"
                        response = await client.get(f"https://api.github.com/repos/{path}/commits/HEAD", headers=headers)
                
                response.raise_for_status()
                sha = response.json().get("sha", "").lower()
        except Exception:
            raise HTTPException(status_code=503, detail="Failed to resolve HEAD commit from GitHub")"""
content = content.replace(old_queue, new_queue)

# 3. Update create_repository
old_create = """@router.post("/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    url = validate_github_url(repo.url)
    existing = (await db.execute(select(Repository).where(Repository.owner_id == current_user.id, Repository.url == url))).scalars().first()
    if existing: return existing
    db_repo = Repository(name=repo.name.strip()[:255], url=url, owner_id=current_user.id); db.add(db_repo); await db.commit(); await db.refresh(db_repo)
    return db_repo"""

new_create = """from dateutil.parser import parse as parse_date
@router.post("/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    canonical_url, owner, repo_name = validate_github_url(repo.url)
    existing = (await db.execute(select(Repository).where(Repository.owner_id == current_user.id, Repository.url == canonical_url))).scalars().first()
    if existing: return existing
    
    # Fetch public metadata
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
            # Check if user has token to avoid rate limits, else do anonymous
            token = decrypt_token(current_user.github_access_token) if current_user.github_access_token else None
            if token:
                headers["Authorization"] = f"Bearer {token}"
                
            response = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
            
            if response.status_code == 404:
                raise HTTPException(status_code=400, detail="Repository not found or is private")
                
            response.raise_for_status()
            data = response.json()
            
            if data.get("private"):
                raise HTTPException(status_code=400, detail="This repository is private. Public repositories are supported without GitHub account connection.")
                
            db_repo = Repository(
                name=data.get("full_name") or f"{owner}/{repo_name}",
                url=canonical_url,
                owner_id=current_user.id,
                provider="github",
                github_owner=owner,
                default_branch=data.get("default_branch"),
                is_public=not data.get("private"),
                github_created_at=parse_date(data.get("created_at")) if data.get("created_at") else None,
                github_updated_at=parse_date(data.get("updated_at")) if data.get("updated_at") else None,
                monitoring_enabled=True
            )
            db.add(db_repo)
            await db.commit()
            await db.refresh(db_repo)
            return db_repo
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Failed to communicate with GitHub API")
"""
content = content.replace(old_create, new_create)

with open("backend/app/api/routes/repositories.py", "w", encoding="utf-8") as f:
    f.write(content)
