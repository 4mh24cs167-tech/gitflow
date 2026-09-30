with open("backend/app/workers/polling.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement_loop = """
etag_cache = {}

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
                                
                                # Check latest commit for Etag
                                headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
                                if repo.id in etag_cache:
                                    headers["If-None-Match"] = etag_cache[repo.id]
                                    
                                url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={repo.default_branch or 'HEAD'}&per_page=1"
                                response = await client.get(url, headers=headers)
                                
                                if response.status_code == 304:
                                    # No changes
                                    continue
                                    
                                if response.status_code == 200:
                                    if "etag" in response.headers:
                                        etag_cache[repo.id] = response.headers["etag"]
                                        
                                # Fetch commits from GitHub
"""

import re
content = re.sub(r"async def repository_polling_loop\(\):.*?# Fetch commits from GitHub", replacement_loop, content, flags=re.DOTALL)

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    f.write(content)
