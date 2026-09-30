with open("backend/app/workers/polling.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
replacement = """        url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?sha={default_branch}&per_page=30&page={page}"
        response = await client.get(url, headers=headers)
        if response.status_code in (403, 429):
            reset_time = response.headers.get("x-ratelimit-reset")
            retry_after = response.headers.get("retry-after")
            
            wait_seconds = 60
            import time
            if retry_after:
                wait_seconds = int(retry_after)
            elif reset_time:
                wait_seconds = max(60, int(reset_time) - int(time.time()))
            
            print(f"Rate limited by GitHub. Waiting {wait_seconds} seconds.")
            await asyncio.sleep(wait_seconds)
            continue
"""

content = re.sub(r"\s+url = f\"https://api\.github\.com/repos/\{owner\}/\{repo_name\}/commits\?sha=\{default_branch\}&per_page=30&page=\{page\}\".*?continue", replacement, content, flags=re.DOTALL)

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    f.write(content)
