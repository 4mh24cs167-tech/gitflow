import re
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.config import settings
from app.database.models import Commit, Repository, Scan, User
from app.auth.security import decrypt_token
from app.database.session import get_db
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.workers.scan_job import run_scan

router = APIRouter(prefix="/repositories", tags=["repositories"])
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")

def validate_github_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise HTTPException(status_code=422, detail="Only HTTPS github.com repository URLs are supported")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path.endswith(".git"):
        raise HTTPException(status_code=422, detail="Invalid repository URL")
    return f"https://github.com{parsed.path}"

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else request.cookies.get("access_token", "")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username or payload.get("type") != "access": raise JWTError("invalid access token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    user = (await db.execute(select(User).where(User.username == username, User.is_active.is_(True)))).scalars().first()
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

async def owned_repository(repository_id: int, current_user: User, db: AsyncSession) -> Repository:
    repo = (await db.execute(select(Repository).where(Repository.id == repository_id, Repository.owner_id == current_user.id))).scalars().first()
    if not repo: raise HTTPException(status_code=404, detail="Repository not found")
    return repo

async def queue_scan(repository_id: int, commit_sha: str, current_user: User, db: AsyncSession) -> tuple[Scan, bool]:
    sha = commit_sha.lower()
    
    if sha == "head":
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
            del plain_token

    if not SHA_RE.fullmatch(sha): 
        raise HTTPException(status_code=422, detail="commit_sha must be a full 40-character Git commit SHA")
        
    commit = (await db.execute(select(Commit).where(Commit.repository_id == repository_id, Commit.hash == sha))).scalars().first()
    if not commit:
        commit = Commit(repository_id=repository_id, hash=sha, message="Commit scan"); db.add(commit); await db.flush()
    scan = (await db.execute(select(Scan).where(Scan.commit_id == commit.id))).scalars().first()
    if scan: return scan, False
    scan = Scan(commit_id=commit.id, status="QUEUED"); db.add(scan); await db.commit(); await db.refresh(scan)
    return scan, True

@router.post("/", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    url = validate_github_url(repo.url)
    existing = (await db.execute(select(Repository).where(Repository.owner_id == current_user.id, Repository.url == url))).scalars().first()
    if existing: return existing
    db_repo = Repository(name=repo.name.strip()[:255], url=url, owner_id=current_user.id); db.add(db_repo); await db.commit(); await db.refresh(db_repo)
    return db_repo

@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(Repository).where(Repository.owner_id == current_user.id))).scalars())

@router.get("/github")
async def list_github_repositories(current_user: User = Depends(get_current_user)):
    if not current_user.github_access_token: 
        raise HTTPException(status_code=409, detail="GitHub authentication required")
        
    plain_token = decrypt_token(current_user.github_access_token)
    if not plain_token:
        raise HTTPException(status_code=409, detail="GitHub authentication required (invalid token)")
        
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get("https://api.github.com/user/repos?per_page=100&sort=updated", headers={"Authorization": f"Bearer {plain_token}", "Accept": "application/vnd.github+json"})
    except httpx.HTTPError: raise HTTPException(status_code=503, detail="GitHub is unavailable")
    if response.status_code in {401, 403}: raise HTTPException(status_code=409, detail="GitHub authentication or repository access is required")
    if response.status_code != 200: raise HTTPException(status_code=503, detail="GitHub repository listing is unavailable")
    
    # Securely discard plain token
    del plain_token
    
    return [{"id": r["id"], "name": r["full_name"], "url": r["clone_url"], "language": r.get("language")} for r in response.json()]

@router.post("/{repository_id}/scan")
async def trigger_manual_scan(repository_id: int, commit_sha: str, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scan, created = await queue_scan(repository_id, commit_sha, current_user, db)
    if created: background_tasks.add_task(run_scan, scan.id)
    return {"scan_id": scan.id, "status": scan.status, "queued": created}

@router.get("/{repository_id}/scans")
async def get_repository_scans(repository_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scans = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Commit.repository_id == repository_id).order_by(Scan.created_at.desc()))).scalars().all()
    return [{"id": s.id, "commit_sha": s.commit.hash, "status": s.status, "score": s.risk_score.score if s.risk_score else None, "score_details": s.risk_score.details if s.risk_score else None, "created_at": s.created_at, "findings_count": len(s.findings)} for s in scans]

@router.get("/{repository_id}/risk-history")
async def get_risk_history(repository_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scans = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score)).where(Commit.repository_id == repository_id, Scan.status == "COMPLETED").order_by(Scan.completed_at.asc()))).scalars().all()
    return [{"commit_sha": s.commit.hash, "short_sha": s.commit.hash[:7], "risk_score": s.risk_score.score if s.risk_score else 100, "score_delta": s.risk_score.score_delta if s.risk_score else None, "scanned_at": s.completed_at, "commit_message": s.commit.message} for s in scans]
