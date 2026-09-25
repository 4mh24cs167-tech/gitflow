import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from app.database.session import get_db
from app.database.models import Repository, User
from app.workers.scan_job import run_scan
from app.api.routes.repositories import queue_scan

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header:
        return False
    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    signature = request.headers.get("x-hub-signature-256")
    body = await request.body()
    
    if not verify_signature(body, signature, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook payload")
    
    event_type = request.headers.get("x-github-event")
    if event_type == "push":
        repo_url = payload.get("repository", {}).get("clone_url")
        commit_sha = payload.get("after")
        
        if repo_url and commit_sha:
            # Find repository by url
            result = await db.execute(select(Repository).where(Repository.url == repo_url))
            repo = result.scalars().first()
            if repo:
                owner = (await db.execute(select(User).where(User.id == repo.owner_id))).scalars().first()
                if not owner:
                    raise HTTPException(status_code=404, detail="Repository owner not found")
                scan, created = await queue_scan(repo.id, commit_sha, owner, db)
                if created:
                    background_tasks.add_task(run_scan, scan.id)
                return {"message": "Scan queued" if created else "Duplicate delivery ignored", "scan_id": scan.id}
            else:
                return {"message": "Repository not tracked"}
    
    return {"message": "Event ignored"}
