with open("backend/app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(
    r"from app\.workers\.polling import repository_polling_loop\s+task = asyncio\.create_task\(repository_polling_loop\(\)\)\s+yield\s+task\.cancel\(\)\s+try:\s+await task\s+except asyncio\.CancelledError:\s+pass",
    "yield",
    content
)

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(content)
