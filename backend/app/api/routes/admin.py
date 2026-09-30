import asyncio
import subprocess
import logging
import time
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import Repository, Scan, Commit
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def verify_cron_secret(request: Request) -> None:
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=503, detail="Cron secret not configured")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if not token or token != settings.CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

# ---------------------------------------------------------------------------
# Database-level concurrency lock
# ---------------------------------------------------------------------------

async def acquire_poll_lock(db) -> bool:
    """Acquire a robust database lock. Fails safely on DB error."""
    try:
        is_pg = db.bind.dialect.name == "postgresql"
        if is_pg:
            # Native PostgreSQL advisory lock (session-level)
            res = await db.execute(text("SELECT pg_try_advisory_lock(13371337)"))
            return bool(res.scalar())
        else:
            # Atomic row-based lease for SQLite
            await db.execute(text("CREATE TABLE IF NOT EXISTS polling_lock (id INTEGER PRIMARY KEY, locked_at TEXT)"))
            await db.execute(text("INSERT OR IGNORE INTO polling_lock (id, locked_at) VALUES (1, NULL)"))
            await db.commit()
            
            now_str = datetime.now(timezone.utc).isoformat()
            stale_seconds = settings.MAX_POLLING_RUNTIME_SECONDS + 60
            stale_time = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).isoformat()
            
            res = await db.execute(text(
                "UPDATE polling_lock SET locked_at = :now WHERE id = 1 AND (locked_at IS NULL OR locked_at < :stale)"
            ), {"now": now_str, "stale": stale_time})
            await db.commit()
            return res.rowcount > 0
    except Exception as e:
        logger.error("Lock acquisition failed: %s", e)
        # Fail safely: do NOT proceed
        return False

async def release_poll_lock(db):
    try:
        is_pg = db.bind.dialect.name == "postgresql"
        if is_pg:
            await db.execute(text("SELECT pg_advisory_unlock(13371337)"))
        else:
            await db.execute(text("UPDATE polling_lock SET locked_at = NULL WHERE id = 1"))
            await db.commit()
    except Exception as e:
        logger.error("Lock release failed: %s", e)

# ---------------------------------------------------------------------------
# Core Monitoring Logic
# ---------------------------------------------------------------------------

def resolve_remote_head(url: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True, text=True, timeout=15,
            env={**__import__("os").environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        if result.returncode == 0 and result.stdout.strip():
            sha = result.stdout.strip().split()[0].lower()
            if len(sha) == 40:
                return sha
    except Exception as e:
        logger.warning("git ls-remote failed for %s: %s", url, e)
    return None

async def fetch_missing_commits(
    owner: str, repo_name: str, default_branch: str, last_processed_sha: str | None, max_commits: int
) -> dict:
    import httpx
    fetched_commits = []
    page = 1
    found_anchor = False
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={default_branch}&per_page=30&page={page}"
            response = await client.get(url, headers=headers)

            if response.status_code in (403, 429):
                return {"status": "rate_limited", "commits": []}
            if response.status_code != 200:
                return {"status": "api_error", "commits": []}
            
            data = response.json()
            if not data:
                break

            if not last_processed_sha and page == 1:
                return {
                    "status": "success",
                    "commits": [{"sha": data[0]["sha"], "message": data[0].get("commit", {}).get("message", "")}]
                }

            for c in data:
                sha = c["sha"]
                if sha == last_processed_sha:
                    found_anchor = True
                    break
                fetched_commits.append({"sha": sha, "message": c.get("commit", {}).get("message", "")})

            if found_anchor or page > 100:
                break
            page += 1

    if last_processed_sha and not found_anchor:
        return {"status": "anchor_not_found", "commits": []}

    fetched_commits.reverse()
    return {"status": "success", "commits": fetched_commits[:max_commits]}

async def process_one_repository(repo_id: int, semaphore: asyncio.Semaphore, deadline: float) -> dict:
    result = {"repo_id": repo_id, "changed": False, "commits_discovered": 0, "commits_queued": 0, "error": None, "partial": False}

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.id == repo_id))).scalars().first()
        if not repo or repo.monitoring_status != "POLLING_ACTIVE":
            return result

        now = datetime.now(timezone.utc)
        try:
            canonical_url, owner, repo_name = get_canonical_github_url(repo.url)
            branch = repo.default_branch or "main"

            remote_head = await asyncio.to_thread(resolve_remote_head, f"{canonical_url}.git")
            if not remote_head:
                repo.last_poll_error = "git ls-remote failed"
                repo.last_polled_at = now
                await db.commit()
                result["error"] = "git ls-remote failed"
                return result

            repo.last_seen_sha = remote_head
            repo.last_polled_at = now

            last_processed_sha = repo.last_processed_sha
            if not last_processed_sha:
                last_successful_scan = (await db.execute(
                    select(Scan).join(Commit)
                    .where(Commit.repository_id == repo.id, Scan.status == "COMPLETED")
                    .order_by(Scan.created_at.desc()).limit(1)
                )).scalars().first()
                if last_successful_scan:
                    last_commit = (await db.execute(select(Commit).where(Commit.id == last_successful_scan.commit_id))).scalars().first()
                    if last_commit:
                        last_processed_sha = last_commit.hash
                        repo.last_processed_sha = last_processed_sha

            if remote_head == last_processed_sha:
                repo.last_poll_error = None
                repo.last_successful_poll_at = now
                await db.commit()
                return result

            result["changed"] = True
            fetch_result = await fetch_missing_commits(owner, repo_name, branch, last_processed_sha, settings.MAX_COMMITS_PER_POLL)
            
            if fetch_result["status"] in ("rate_limited", "api_error"):
                repo.last_poll_error = f"GitHub API: {fetch_result['status']}"
                await db.commit()
                result["error"] = fetch_result["status"]
                return result
                
            if fetch_result["status"] == "anchor_not_found":
                repo.last_poll_error = "ANCHOR_NOT_FOUND: history rewrite detected"
                repo.monitoring_status = "ERROR"
                await db.commit()
                result["error"] = "anchor_not_found"
                return result

            missing_commits = fetch_result["commits"]
            result["commits_discovered"] = len(missing_commits)

            for commit_data in missing_commits:
                # Runtime budget reservation: Do we have enough time for a scan?
                remaining = deadline - time.time()
                SAFETY_MARGIN_SECONDS = 15
                if remaining <= (settings.SCAN_TIMEOUT_SECONDS + SAFETY_MARGIN_SECONDS):
                    result["partial"] = True
                    break

                sha = commit_data["sha"]
                commit = (await db.execute(select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha))).scalars().first()

                if not commit:
                    # Savepoint (nested transaction) to safely catch IntegrityError
                    async with db.begin_nested():
                        try:
                            commit = Commit(repository_id=repo.id, hash=sha, message=commit_data["message"])
                            db.add(commit)
                            await db.flush()
                        except IntegrityError:
                            # Safely caught, rollback only this sub-transaction
                            pass
                    if not commit.id:
                        commit = (await db.execute(select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha))).scalars().first()
                        if not commit:
                            continue

                existing_scan = (await db.execute(select(Scan).where(Scan.commit_id == commit.id))).scalars().first()

                if existing_scan:
                    if existing_scan.status == "COMPLETED":
                        repo.last_processed_sha = sha
                        await db.commit()
                        continue
                    elif existing_scan.status in ("QUEUED", "RUNNING"):
                        # Active legitimate scan by another worker/trigger: preserve it and stop here for this repo
                        await db.commit()
                        return result
                    
                    # FAILED scan retry: delete it so we can create a fresh QUEUED scan without IntegrityError on commit_id
                    await db.delete(existing_scan)
                    await db.flush()

                new_scan = Scan(commit_id=commit.id, status="QUEUED")
                async with db.begin_nested():
                    try:
                        db.add(new_scan)
                        await db.flush()
                    except IntegrityError:
                        pass
                
                if not new_scan.id:
                    continue

                result["commits_queued"] += 1

                async with semaphore:
                    await run_scan(new_scan.id)

                finished_scan = (await db.execute(select(Scan).where(Scan.id == new_scan.id))).scalars().first()
                if finished_scan and finished_scan.status == "COMPLETED":
                    # Persist cursor immediately
                    repo.last_processed_sha = sha
                    repo.last_poll_error = None
                    repo.last_successful_poll_at = now
                    await db.commit()
                else:
                    repo.last_poll_error = f"Scan failed for {sha[:7]}"
                    await db.commit()
                    # A failed commit must halt processing for this repo to maintain chronological order
                    return result

        except Exception as e:
            logger.exception("Error polling repo %s", repo_id)
            try:
                repo.last_poll_error = str(e)[:200]
                repo.monitoring_status = "ERROR"
                await db.commit()
            except Exception:
                pass
            result["error"] = str(e)[:200]

    return result

# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/polling/run")
async def run_polling(request: Request):
    verify_cron_secret(request)

    # Use a single dedicated DB session to hold the lock for the entire request duration
    async with AsyncSessionLocal() as lock_db:
        locked = await acquire_poll_lock(lock_db)
        if not locked:
            return {"status": "skipped", "reason": "Another polling run is in progress or lock failed"}

        try:
            start_time = time.time()
            deadline = start_time + settings.MAX_POLLING_RUNTIME_SECONDS

            async with AsyncSessionLocal() as db:
                repo_ids = (await db.execute(
                    select(Repository.id).where(Repository.monitoring_status.in_(["POLLING_ACTIVE", "ERROR"]))
                )).scalars().all()

            semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCANS)
            results = []
            
            status = "completed"
            for repo_id in repo_ids:
                if time.time() > deadline:
                    status = "partial"
                    break
                
                res = await process_one_repository(repo_id, semaphore, deadline)
                results.append(res)
                if res.get("partial"):
                    status = "partial"
                    break

            summary = {
                "status": status,
                "repositories_checked": len(results),
                "repositories_changed": sum(1 for r in results if r["changed"]),
                "commits_discovered": sum(r["commits_discovered"] for r in results),
                "commits_queued": sum(r["commits_queued"] for r in results),
                "errors": sum(1 for r in results if r["error"]),
            }
            return summary

        finally:
            await release_poll_lock(lock_db)
