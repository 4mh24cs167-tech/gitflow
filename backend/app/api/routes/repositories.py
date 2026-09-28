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
from pydantic import BaseModel

class ScanRequest(BaseModel):
    commit_sha: str

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
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
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
async def trigger_manual_scan(repository_id: int, request: ScanRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scan, created = await queue_scan(repository_id, request.commit_sha, current_user, db)
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
    from sqlalchemy.orm import selectinload
    from app.database.models import Notification
    scans = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score)).where(Commit.repository_id == repository_id, Scan.status == "COMPLETED").order_by(Scan.completed_at.asc()))).scalars().all()
    
    result = []
    for s in scans:
        notifications = (await db.execute(select(Notification).where(Notification.scan_id == s.id))).scalars().all()
        result.append({
            "id": s.id,
            "commit_sha": s.commit.hash, 
            "short_sha": s.commit.hash[:7], 
            "risk_score": s.risk_score.score if s.risk_score else 100, 
            "score_delta": s.risk_score.score_delta if s.risk_score else None, 
            "scanned_at": s.completed_at, 
            "commit_message": s.commit.message,
            "alerts": [n.title for n in notifications]
        })
    return result

from app.database.models import CommitAnalysis

@router.get("/{repository_id}/scans/{scan_id}")
async def get_scan_audit(repository_id: int, scan_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    scan = (await db.execute(select(Scan)
        .join(Scan.commit)
        .options(selectinload(Scan.findings), selectinload(Scan.risk_score), selectinload(Scan.commit), selectinload(Scan.commit_analysis))
        .where(Scan.id == scan_id, Commit.repository_id == repository_id)
    )).scalars().first()
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    analysis = scan.commit_analysis
    import json
    
    actions_detected = []
    if analysis and analysis.actions_detected:
        actions_detected = json.loads(analysis.actions_detected)
        
    changes = []
    if analysis and analysis.changed_files:
        changes = json.loads(analysis.changed_files)
        
    from app.database.models import Notification
    notifications = (await db.execute(select(Notification).where(Notification.scan_id == scan.id))).scalars().all()
    
    score_delta = scan.risk_score.score_delta if scan.risk_score else None
    current_score = scan.risk_score.score if scan.risk_score else None
    previous_score = current_score - score_delta if score_delta is not None and current_score is not None else None
        
    return {
        "id": scan.id,
        "commit_sha": scan.commit.hash,
        "status": scan.status,
        "findings": [{"title": f.type, "description": f.description, "severity": f.severity} for f in scan.findings],
        "changes": changes,
        "risk_score": current_score,
        "previous_score": previous_score,
        "score_delta": score_delta,
        "actions_detected": actions_detected,
        "notifications": [{"id": n.id, "type": n.type, "title": n.title, "message": n.message} for n in notifications]
    }

class AskRequest(BaseModel):
    question: str

@router.post("/{repository_id}/scans/{scan_id}/ask")
async def ask_scan_question(repository_id: int, scan_id: int, request: AskRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await owned_repository(repository_id, current_user, db)
    from sqlalchemy.orm import selectinload
    from app.database.models import Notification
    import json
    
    scan = (await db.execute(select(Scan).join(Scan.commit).options(selectinload(Scan.commit), selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Scan.id == scan_id, Commit.repository_id == repository_id))).scalars().first()
    if not scan: raise HTTPException(status_code=404, detail="Scan not found")
        
    analysis = (await db.execute(select(CommitAnalysis).where(CommitAnalysis.commit_id == scan.commit_id))).scalars().first()
    notifications = (await db.execute(select(Notification).where(Notification.scan_id == scan.id))).scalars().all()
    
    actions = json.loads(analysis.actions_detected) if analysis and analysis.actions_detected else []
    changes = json.loads(analysis.changed_files) if analysis and analysis.changed_files else []
    impact = json.loads(analysis.impact_analysis) if analysis and analysis.impact_analysis else []
    findings = scan.findings
    
    # Intent normalization
    q = request.question.lower().strip()
    
    intents = {
        "what_changed": ["what changed", "what was changed", "tell me what changed", "what did this commit modify", "which files changed", "what changed in this commit", "files modified"],
        "why_risk": ["why did risk increase", "why is the score lower", "why did my score change", "why did the risk score change", "why risk", "score delta", "risk score"],
        "impact": ["what can this affect", "what modules may be affected", "what is affected", "impact", "indirectly affected", "what could be affected indirectly", "affected"],
        "security": ["was anything security related changed", "security", "security-sensitive", "secrets", "auth"],
        "dependencies": ["did dependencies change", "dependencies", "packages"],
        "review": ["what should i review", "review", "which files should i review"],
        "explain": ["explain this commit", "summarize this commit", "explain", "simply", "summary"],
        "alerts": ["what alerts were triggered", "alerts", "notifications"]
    }
    
    matched_intent = None
    for intent, variants in intents.items():
        if any(v in q for v in variants):
            matched_intent = intent
            break
            
    answer = ""
    facts = []
    sources = []
    
    # Score Delta Convention: current_score - previous_score
    # Negative delta = risk decreased (improved)
    # Positive delta = risk increased (worsened)
    
    if matched_intent == "what_changed":
        answer = f"VERIFIED FACT:\nThis commit modified {len(changes)} files."
        if changes:
            answer += "\n\nFiles changed:\n" + "\n".join([f"- {c.get('file', c) if isinstance(c, dict) else c}" for c in changes])
        facts.append(f"{len(changes)} files modified.")
        sources.append("CommitAnalysis.changed_files")
        
    elif matched_intent == "why_risk":
        score_delta = scan.risk_score.score_delta if scan.risk_score else 0
        current_score = scan.risk_score.score if scan.risk_score else 0
        previous_score = current_score - score_delta
        
        if score_delta == 0:
            answer = f"VERIFIED FACT:\nThe risk score did not change (remained at {current_score})."
        else:
            direction = "decreased" if score_delta < 0 else "increased"
            answer = f"VERIFIED FACT:\nThe risk score {direction} by {abs(score_delta)} points (from {previous_score} to {current_score})."
            if findings:
                answer += "\n\nContributing findings (VERIFIED FACT):\n" + "\n".join([f"- {f.description}" for f in findings])
        facts.append(f"Score delta: {score_delta}")
        sources.append("RiskScore.score_delta")
        
    elif matched_intent == "impact":
        if impact:
            answer = "POTENTIAL IMPACT:\nThe following modules could be indirectly affected by this change based on structural dependency rules:\n" + "\n".join([f"- {i}" for i in impact])
            facts.append(f"{len(impact)} modules potentially affected.")
        else:
            answer = "VERIFIED FACT:\nNo indirect module impact was deterministically detected."
        sources.append("CommitAnalysis.impact_analysis")
            
    elif matched_intent == "security":
        sec_actions = [a for a in actions if "auth" in a.lower() or "security" in a.lower()]
        sec_findings = [f.description for f in findings if "secur" in f.type.lower() or f.severity.lower() in ("high", "critical")]
        if sec_actions or sec_findings:
            answer = "VERIFIED FACT:\nSecurity-sensitive events detected:\n"
            if sec_actions:
                answer += "\nActions:\n" + "\n".join([f"- {a}" for a in sec_actions])
            if sec_findings:
                answer += "\n\nFindings:\n" + "\n".join([f"- {f}" for f in sec_findings])
            facts.append("Security modifications/findings present.")
        else:
            answer = "VERIFIED FACT:\nNo explicit security-sensitive changes were detected."
        sources.append("CommitAnalysis.actions_detected")
        sources.append("Findings")
        
    elif matched_intent == "dependencies":
        dep_actions = [a for a in actions if "dependenc" in a.lower()]
        if dep_actions:
            answer = "VERIFIED FACT:\nDependency changes detected:\n" + "\n".join([f"- {a}" for a in dep_actions])
            facts.append("Dependencies modified.")
        else:
            answer = "VERIFIED FACT:\nNo dependency manifest changes were detected."
        sources.append("CommitAnalysis.actions_detected")
        
    elif matched_intent == "review":
        answer = "POTENTIAL IMPACT:\nYou should review files that triggered alerts or direct structural changes."
        if changes:
            answer += "\n\nModified files requiring review:\n" + "\n".join([f"- {c.get('file', c) if isinstance(c, dict) else c}" for c in changes])
        sources.append("CommitAnalysis.changed_files")
        
    elif matched_intent == "alerts":
        if notifications:
            answer = "VERIFIED FACT:\nThe following alerts were triggered:\n" + "\n".join([f"- {n.title}: {n.message}" for n in notifications])
            facts.append(f"{len(notifications)} alerts triggered.")
        else:
            answer = "VERIFIED FACT:\nNo alerts were triggered for this commit."
        sources.append("Notification")
        
    elif matched_intent == "explain":
        answer = f"VERIFIED FACT:\nThis commit by {scan.commit.author} changed {len(changes)} files. "
        if actions:
            answer += f"It performed the following actions: {', '.join(actions)}. "
        if notifications:
            answer += f"It triggered {len(notifications)} alerts."
        sources.append("Commit metadata")
        sources.append("CommitAnalysis.actions_detected")
        
    else:
        answer = "I can answer questions about this commit's changes, risk, impact, security changes, dependencies, alerts, and review areas."
        
    return {
        "question": request.question,
        "answer": answer,
        "facts": facts,
        "sources": sources,
        "confidence": "deterministic"
    }
