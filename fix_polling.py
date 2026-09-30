import re

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    f.write("""import asyncio
import httpx
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import AsyncSessionLocal
from app.database.models import Repository, Scan, Commit
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url

async def fetch_commits_between(client, owner, repo_name, default_branch, last_processed_sha):
    commits_to_process = []
    page = 1
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={default_branch}&per_page=30&page={page}"
        response = await client.get(url, headers=headers)
        if response.status_code == 403 or response.status_code == 429:
            # Rate limited, pause
            await asyncio.sleep(60)
            continue
        if response.status_code != 200:
            break
            
        commits = response.json()
        if not commits:
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
        
    return reversed(commits_to_process)

async def repository_polling_loop():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                repos = (await db.execute(
                    select(Repository).where(Repository.monitoring_status == "POLLING_ACTIVE")
                )).scalars().all()
                
                if repos:
                    async with httpx.AsyncClient(timeout=10) as client:
                        for repo in repos:
                            try:
                                _, owner, repo_name = get_canonical_github_url(repo.url)
                                
                                # Find the last processed SHA
                                last_scan = (await db.execute(
                                    select(Scan)
                                    .join(Commit)
                                    .where(Commit.repository_id == repo.id)
                                    .order_by(Scan.created_at.desc())
                                    .limit(1)
                                )).scalars().first()
                                
                                last_processed_sha = None
                                if last_scan:
                                    last_commit = (await db.execute(select(Commit).where(Commit.id == last_scan.commit_id))).scalars().first()
                                    if last_commit:
                                        last_processed_sha = last_commit.hash
                                
                                # Fetch commits from GitHub
                                commits = await fetch_commits_between(
                                    client, owner, repo_name, repo.default_branch or "HEAD", last_processed_sha
                                )
                                
                                for commit_data in commits:
                                    sha = commit_data["sha"]
                                    # Ensure duplicate safety
                                    existing_commit = (await db.execute(
                                        select(Commit).where(Commit.repository_id == repo.id, Commit.hash == sha)
                                    )).scalars().first()
                                    
                                    if not existing_commit:
                                        new_commit = Commit(repository_id=repo.id, hash=sha, message=commit_data["message"])
                                        db.add(new_commit)
                                        await db.commit()
                                        await db.refresh(new_commit)
                                        
                                        new_scan = Scan(commit_id=new_commit.id, status="QUEUED")
                                        db.add(new_scan)
                                        await db.commit()
                                        await db.refresh(new_scan)
                                        
                                        # Use asyncio to launch worker immediately, but bound concurrency via the worker architecture ideally.
                                        # Here we simply spawn it
                                        asyncio.create_task(run_scan(new_scan.id))
                                
                            except Exception as e:
                                print(f"Error polling repo {repo.id}: {e}")
                            
                            await asyncio.sleep(2)
                            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Polling loop error: {e}")
            
        await asyncio.sleep(300) # Poll every 5 minutes

if __name__ == "__main__":
    asyncio.run(repository_polling_loop())
""")
