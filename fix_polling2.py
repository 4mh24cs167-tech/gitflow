with open("backend/app/workers/polling.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = content.replace("""        if not commits:
            break
            
        found = False
        for c in commits:""", """        if not commits:
            break
            
        # If there's no last processed SHA (e.g. brand new repository that failed initial scan),
        # just take the very first commit (the latest) and stop, to prevent scanning entire history.
        if not last_processed_sha and page == 1:
            commits_to_process.append({
                "sha": commits[0]["sha"],
                "message": commits[0].get("commit", {}).get("message", "")
            })
            break

        found = False
        for c in commits:""")

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    f.write(content)
