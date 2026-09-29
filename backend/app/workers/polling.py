import asyncio
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import AsyncSessionLocal
from app.database.models import Repository, Scan, Commit
from app.workers.scan_job import run_scan
from app.utils.github import get_canonical_github_url

async def repository_polling_loop():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find repositories with monitoring_status == "POLLING_ACTIVE"
                repos = (await db.execute(
                    select(Repository).where(Repository.monitoring_status == "POLLING_ACTIVE")
                )).scalars().all()
                
                if repos:
                    async with httpx.AsyncClient(timeout=10) as client:
                        for repo in repos:
                            try:
                                _, owner, repo_name = get_canonical_github_url(repo.url)
                                headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
                                # If owner has a token, use it to avoid rate limits? We don't have access to the owner's token here easily unless we load the user.
                                # For now, just anonymous polling
                                response = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}/commits/{repo.default_branch or 'HEAD'}", headers=headers)
                                if response.status_code == 200:
                                    latest_sha = response.json()["sha"]
                                    
                                    # Check if we already have this commit scanned
                                    existing_commit = (await db.execute(
                                        select(Commit).where(Commit.repository_id == repo.id, Commit.hash == latest_sha)
                                    )).scalars().first()
                                    
                                    if not existing_commit:
                                        # Create new commit and scan
                                        new_commit = Commit(repository_id=repo.id, hash=latest_sha, message=response.json().get("commit", {}).get("message", ""))
                                        db.add(new_commit)
                                        await db.commit()
                                        await db.refresh(new_commit)
                                        
                                        new_scan = Scan(commit_id=new_commit.id, status="QUEUED")
                                        db.add(new_scan)
                                        await db.commit()
                                        await db.refresh(new_scan)
                                        
                                        # Run the worker directly as a background task
                                        asyncio.create_task(run_scan(new_scan.id))
                            except Exception as e:
                                print(f"Error polling repo {repo.id}: {e}")
                            
                            await asyncio.sleep(2) # rate limit prevention between repos
                            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Polling loop error: {e}")
            
        await asyncio.sleep(60) # Poll every 60 seconds
