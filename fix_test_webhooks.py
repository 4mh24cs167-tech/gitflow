with open("backend/tests/test_webhooks.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
replacement = """    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    from app.config import settings
    signature = "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256).hexdigest()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/webhooks/github",
            headers={"x-hub-signature-256": signature, "x-github-event": "push", "content-type": "application/json"},
            content=payload_bytes
        )"""

content = re.sub(r"\s+import json.*?json=payload\n\s+\)", replacement, content, flags=re.DOTALL)

with open("backend/tests/test_webhooks.py", "w", encoding="utf-8") as f:
    f.write(content)
