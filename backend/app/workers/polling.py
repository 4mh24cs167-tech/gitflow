import asyncio
import httpx
import os
import time
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import AsyncSessionLocal
from app.database.models import Repository, Scan, Commit
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url

MAX_CONCURRENT_SCANS = int(os.getenv("MAX_CONCURRENT_SCANS", "2"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))

etag_cache = {}

async def fetch_commits_between(client, owner, repo_name, default_branch, last_processed_sha):
    commits_to_process = []
    page = 1
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={default_branch}&per_page=30&page={page}"
        response = await client.get(url, headers=headers)
        if response.status_code in (403, 429):
            reset_time = response.headers.get("x-ratelimit-reset")
            retry_after = response.headers.get("retry-after")
            wait_seconds = 60
            if retry_after:
                wait_seconds = int(retry_after)
            elif reset_time:
                wait_seconds = max(60, int(reset_time) - int(time.time()))
            print(f"Rate limited by GitHub. Waiting {wait_seconds} seconds.")
            await asyncio.sleep(wait_seconds)
            continue

        if response.status_code != 200:
            break
            
        commits = response.json()
        if not commits:
            break
            
        if not last_processed_sha and page == 1:
            commits_to_process.append({
                "sha": commits[0]["sha"],
                "message": commits[0].get("commit", {}).get("message", "")
            })
            break

        found = False
        for c in commits:
            sha = c["sha"]
            if sha == last_processed_sha:
                found = True
                break
            commits_to_process.append({
                "sha": sha,
                "message": c.get("commit", {}).get("message", "")
            })
            
        if found:
            break
        page += 1
        
    return list(reversed(commits_to_process))

async def process_repository(repo_id: int, semaphore: asyncio.Semaphore):
    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.id == repo_id))).scalars().first()
        if not repo or repo.monitoring_status != "POLLING_ACTIVE":
            return
            
        try:
            _, owner, repo_name = get_canonical_github_url(repo.url)
            
            last_successful_scan = (await db.execute(
                select(Scan)
                .join(Commit)
                .where(Commit.repository_id == repo.id, Scan.status == "COMPLETED")
                .order_by(Scan.created_at.desc())
                .limit(1)
            )).scalars().first()
            
            last_processed_sha = None
            if last_successful_scan:
                last_commit = (await db.execute(select(Commit).where(Commit.id == last_successful_scan.commit_id))).scalars().first()
                if last_commit:
                    last_processed_sha = last_commit.hash
            
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
                
                if repo.id in etag_cache:
                    headers["If-None-Match"] = etag_cache[repo.id]
                    
                url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={repo.default_branch or 'HEAD'}&per_page=1"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 304:
                    return 
                    
                if response.status_code == 200:
                    if "etag" in response.headers:
                        etag_cache[repo.id] = response.headers["etag"]
                
                commits = await fetch_commits_between(
                    client, owner, repo_name, repo.default_branch or "HEAD", last_processed_sha
                )
                
                for commit_data in commits:
                    sha = commit_data["sha"]
                    
                    commit = (await db.execute(
                        select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha)
                    )).scalars().first()
                    
                    if not commit:
                        commit = Commit(repository_id=repo.id, hash=sha, message=commit_data["message"])
                        db.add(commit)
                        await db.commit()
                        await db.refresh(commit)
                        
                    latest_scan = (await db.execute(
                        select(Scan)
                        .where(Scan.commit_id == commit.id)
                        .order_by(Scan.created_at.desc())
                        .limit(1)
                    )).scalars().first()
                    
                    if latest_scan and latest_scan.status == "COMPLETED":
                        continue
                        
                    if latest_scan and latest_scan.status in ("QUEUED", "RUNNING"):
                        return
                        
                    new_scan = Scan(commit_id=commit.id, status="QUEUED")
                    db.add(new_scan)
                    await db.commit()
                    await db.refresh(new_scan)
                    
                    async with semaphore:
                        await run_scan(new_scan.id)
                        
                    finished_scan = (await db.execute(select(Scan).where(Scan.id == new_scan.id))).scalars().first()
                    if finished_scan and finished_scan.status != "COMPLETED":
                        return 
                        
        except Exception as e:
            print(f"Error processing repo {repo_id}: {e}")

async def repository_polling_loop():
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                repos = (await db.execute(
                    select(Repository.id).where(Repository.monitoring_status == "POLLING_ACTIVE")
                )).scalars().all()
                
            if repos:
                tasks = [process_repository(repo_id, semaphore) for repo_id in repos]
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Polling loop error: {e}")
            
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(repository_polling_loop())
