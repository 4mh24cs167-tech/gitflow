"""
Secure scheduled polling endpoint for public repository monitoring.

Called by GitHub Actions on a cron schedule. NOT embedded in the FastAPI
web process as a background daemon.

Architecture:
  GitHub Actions (cron) → POST /admin/polling/run → this endpoint
  → lightweight HEAD detection via git ls-remote
  → every-commit discovery via GitHub commits API
  → existing exact-SHA scan pipeline
"""
import asyncio
import subprocess
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import Repository, Scan, Commit
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Authentication: dedicated cron secret, NOT a user JWT
# ---------------------------------------------------------------------------

def verify_cron_secret(request: Request) -> None:
    """Reject requests without a valid GITFLOW_CRON_SECRET bearer token."""
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=503, detail="Cron secret not configured")
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if not token or token != settings.CRON_SECRET:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

# ---------------------------------------------------------------------------
# Lightweight HEAD detection using git ls-remote (no REST API quota)
# ---------------------------------------------------------------------------

def resolve_remote_head(url: str) -> str | None:
    """Run `git ls-remote <url> HEAD` to get the current HEAD SHA.
    
    This is a lightweight network operation — no clone, no checkout,
    no code execution, no GitHub REST API quota consumed.
    """
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
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning("git ls-remote failed for %s: %s", url, e)
    return None

# ---------------------------------------------------------------------------
# Commit history discovery via GitHub public API
# ---------------------------------------------------------------------------

async def fetch_missing_commits(
    owner: str,
    repo_name: str,
    default_branch: str,
    last_processed_sha: str | None,
    max_commits: int,
) -> list[dict]:
    """Page through GitHub commits API to find all commits after last_processed_sha.
    
    Returns commits in chronological order (oldest first).
    Stops at max_commits to bound work per invocation.
    """
    import httpx
    
    commits_to_process = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        while len(commits_to_process) < max_commits:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/commits"
                f"?sha={default_branch}&per_page=30&page={page}"
            )
            response = await client.get(url, headers=headers)

            if response.status_code in (403, 429):
                # Rate limited — record and stop, do NOT busy-loop
                remaining = response.headers.get("x-ratelimit-remaining", "?")
                reset = response.headers.get("x-ratelimit-reset")
                logger.warning(
                    "GitHub rate limited (remaining=%s, reset=%s)", remaining, reset
                )
                break

            if response.status_code != 200:
                logger.warning("GitHub API returned %s", response.status_code)
                break

            data = response.json()
            if not data:
                break

            # If there's no baseline SHA, take only the latest commit to
            # establish a starting point (don't scan entire history)
            if not last_processed_sha and page == 1:
                commits_to_process.append({
                    "sha": data[0]["sha"],
                    "message": data[0].get("commit", {}).get("message", ""),
                })
                break

            found_anchor = False
            for c in data:
                sha = c["sha"]
                if sha == last_processed_sha:
                    found_anchor = True
                    break
                commits_to_process.append({
                    "sha": sha,
                    "message": c.get("commit", {}).get("message", ""),
                })

            if found_anchor:
                break
            page += 1
            if page > 10:
                # Safety: don't page indefinitely
                break

    # Return in chronological order: oldest → newest
    commits_to_process.reverse()
    # Trim to max_commits
    return commits_to_process[:max_commits]

# ---------------------------------------------------------------------------
# Process a single repository
# ---------------------------------------------------------------------------

async def process_one_repository(
    repo_id: int,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Process a single repository. Returns a summary dict."""
    result = {"repo_id": repo_id, "changed": False, "commits_discovered": 0, "commits_queued": 0, "error": None}

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(
            select(Repository).where(Repository.id == repo_id)
        )).scalars().first()

        if not repo or repo.monitoring_status != "POLLING_ACTIVE":
            return result

        now = datetime.now(timezone.utc)
        try:
            canonical_url, owner, repo_name = get_canonical_github_url(repo.url)
            branch = repo.default_branch or "main"

            # ---- Step 1: Lightweight HEAD detection ----
            remote_head = await asyncio.to_thread(
                resolve_remote_head, f"{canonical_url}.git"
            )
            if not remote_head:
                repo.last_poll_error = "git ls-remote failed"
                repo.last_polled_at = now
                await db.commit()
                result["error"] = "git ls-remote failed"
                return result

            repo.last_seen_sha = remote_head
            repo.last_polled_at = now

            # ---- Step 2: Determine last processed SHA ----
            # The durable cursor: only COMPLETED scans count
            last_processed_sha = repo.last_processed_sha

            if not last_processed_sha:
                # Derive from DB if the column hasn't been populated yet
                last_successful_scan = (await db.execute(
                    select(Scan)
                    .join(Commit)
                    .where(
                        Commit.repository_id == repo.id,
                        Scan.status == "COMPLETED",
                    )
                    .order_by(Scan.created_at.desc())
                    .limit(1)
                )).scalars().first()
                if last_successful_scan:
                    last_commit = (await db.execute(
                        select(Commit).where(Commit.id == last_successful_scan.commit_id)
                    )).scalars().first()
                    if last_commit:
                        last_processed_sha = last_commit.hash
                        repo.last_processed_sha = last_processed_sha

            # ---- Step 3: Quick check — has HEAD changed? ----
            if remote_head == last_processed_sha:
                repo.last_poll_error = None
                repo.last_successful_poll_at = now
                await db.commit()
                return result  # No new commits

            result["changed"] = True

            # ---- Step 4: Discover every missing commit ----
            missing_commits = await fetch_missing_commits(
                owner, repo_name, branch, last_processed_sha,
                settings.MAX_COMMITS_PER_POLL,
            )
            result["commits_discovered"] = len(missing_commits)

            # ---- Step 5: Process each commit chronologically ----
            for commit_data in missing_commits:
                sha = commit_data["sha"]

                # Create commit record (duplicate-safe)
                commit = (await db.execute(
                    select(Commit).where(
                        Commit.repository_id == repo.id,
                        Commit.hash == sha,
                    )
                )).scalars().first()

                if not commit:
                    commit = Commit(
                        repository_id=repo.id,
                        hash=sha,
                        message=commit_data["message"],
                    )
                    db.add(commit)
                    try:
                        await db.flush()
                    except IntegrityError:
                        await db.rollback()
                        # Another process already created it
                        commit = (await db.execute(
                            select(Commit).where(
                                Commit.repository_id == repo.id,
                                Commit.hash == sha,
                            )
                        )).scalars().first()
                        if not commit:
                            continue

                # Check for existing scan
                existing_scan = (await db.execute(
                    select(Scan).where(Scan.commit_id == commit.id)
                )).scalars().first()

                if existing_scan:
                    if existing_scan.status == "COMPLETED":
                        # Already processed — advance cursor and continue
                        repo.last_processed_sha = sha
                        await db.commit()
                        continue
                    elif existing_scan.status in ("QUEUED", "RUNNING"):
                        # Another process is handling it — stop here for this repo
                        await db.commit()
                        return result
                    # FAILED — we'll retry by creating a new scan below
                    # But first, the old scan has unique=True on commit_id
                    # So we must delete the failed scan to create a new one
                    await db.delete(existing_scan)
                    await db.flush()

                # Create scan
                new_scan = Scan(commit_id=commit.id, status="QUEUED")
                db.add(new_scan)
                try:
                    await db.commit()
                    await db.refresh(new_scan)
                except IntegrityError:
                    await db.rollback()
                    # Race condition: another process created a scan
                    continue

                result["commits_queued"] += 1

                # Execute scan with bounded concurrency
                async with semaphore:
                    await run_scan(new_scan.id)

                # Check result
                finished_scan = (await db.execute(
                    select(Scan).where(Scan.id == new_scan.id)
                )).scalars().first()

                if finished_scan and finished_scan.status == "COMPLETED":
                    repo.last_processed_sha = sha
                    await db.commit()
                else:
                    # Scan failed — stop processing this repo
                    # Next invocation will retry from this point
                    repo.last_poll_error = f"Scan failed for {sha[:7]}"
                    await db.commit()
                    return result

            # All commits processed successfully
            repo.last_poll_error = None
            repo.last_successful_poll_at = now
            await db.commit()

        except Exception as e:
            logger.exception("Error polling repo %s", repo_id)
            try:
                repo.last_poll_error = str(e)[:200]
                repo.last_polled_at = now
                repo.monitoring_status = "ERROR"
                await db.commit()
            except Exception:
                pass
            result["error"] = str(e)[:200]

    return result

# ---------------------------------------------------------------------------
# Database-level concurrency lock
# ---------------------------------------------------------------------------

async def acquire_poll_lock(db) -> bool:
    """Use a simple database row as an advisory lock.
    
    Creates a singleton polling_lock row. If it already exists with
    a recent timestamp (< 5 minutes), another run is in progress.
    """
    from app.database.models import Base
    from sqlalchemy import text
    
    try:
        result = await db.execute(
            text("SELECT locked_at FROM polling_lock WHERE id = 1")
        )
        row = result.first()
        if row:
            locked_at = row[0]
            if locked_at:
                from datetime import timedelta
                # If the lock is stale (> 5 minutes), break it
                if isinstance(locked_at, str):
                    locked_at = datetime.fromisoformat(locked_at)
                if locked_at.tzinfo is None:
                    locked_at = locked_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - locked_at < timedelta(minutes=5):
                    return False  # Another run is active
            await db.execute(
                text("UPDATE polling_lock SET locked_at = :now WHERE id = 1"),
                {"now": datetime.now(timezone.utc).isoformat()},
            )
        else:
            await db.execute(
                text("INSERT INTO polling_lock (id, locked_at) VALUES (1, :now)"),
                {"now": datetime.now(timezone.utc).isoformat()},
            )
        await db.commit()
        return True
    except Exception:
        # Table doesn't exist yet — create it
        try:
            await db.execute(
                text("CREATE TABLE IF NOT EXISTS polling_lock (id INTEGER PRIMARY KEY, locked_at TEXT)")
            )
            await db.execute(
                text("INSERT INTO polling_lock (id, locked_at) VALUES (1, :now)"),
                {"now": datetime.now(timezone.utc).isoformat()},
            )
            await db.commit()
            return True
        except Exception:
            return True  # If we can't lock, proceed anyway to not block monitoring


async def release_poll_lock(db):
    """Release the advisory lock."""
    from sqlalchemy import text
    try:
        await db.execute(
            text("UPDATE polling_lock SET locked_at = NULL WHERE id = 1")
        )
        await db.commit()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------

@router.post("/polling/run")
async def run_polling(request: Request):
    """Secure endpoint triggered by GitHub Actions cron scheduler.
    
    Checks all POLLING_ACTIVE repositories for new commits using
    lightweight git ls-remote, then discovers and processes every
    missing commit in chronological order.
    """
    verify_cron_secret(request)

    async with AsyncSessionLocal() as db:
        locked = await acquire_poll_lock(db)
        if not locked:
            return {
                "status": "skipped",
                "reason": "Another polling run is in progress",
                "repositories_checked": 0,
                "repositories_changed": 0,
                "commits_discovered": 0,
                "commits_queued": 0,
                "errors": 0,
            }

    try:
        # Fetch all active repositories
        async with AsyncSessionLocal() as db:
            repo_ids = (await db.execute(
                select(Repository.id).where(
                    Repository.monitoring_status.in_(["POLLING_ACTIVE", "ERROR"])
                )
            )).scalars().all()

        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCANS)

        # Process repositories sequentially to respect rate limits
        results = []
        for repo_id in repo_ids:
            result = await process_one_repository(repo_id, semaphore)
            results.append(result)

        summary = {
            "status": "completed",
            "repositories_checked": len(results),
            "repositories_changed": sum(1 for r in results if r["changed"]),
            "commits_discovered": sum(r["commits_discovered"] for r in results),
            "commits_queued": sum(r["commits_queued"] for r in results),
            "errors": sum(1 for r in results if r["error"]),
        }

        return summary

    finally:
        async with AsyncSessionLocal() as db:
            await release_poll_lock(db)
