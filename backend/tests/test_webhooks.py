import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.models import Repository, User
from app.database.session import AsyncSessionLocal
from app.utils.github import get_canonical_github_url
import hmac
import hashlib

@pytest.mark.asyncio
async def test_webhook_canonical_url_match():
    async with AsyncSessionLocal() as db:
        # Create a user and a repository with canonical URL
        user = User(username="webhook_user", email="webhook@test.com", hashed_password="pw", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        canonical_url = "https://github.com/owner/repository"
        repo = Repository(owner_id=user.id, name="owner/repository", url=canonical_url)
        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        
    payload = {
        "repository": {
            "clone_url": "https://github.com/owner/repository.git"
        },
        "after": "abcdef123456"
    }
    import json
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    from app.config import settings
    signature = "sha256=" + hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256).hexdigest()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/webhooks/github",
            headers={"x-hub-signature-256": signature, "x-github-event": "push", "content-type": "application/json"},
            content=payload_bytes
        )
        assert res.status_code == 200
        assert res.json()["message"] in ["Scan queued", "Duplicate delivery ignored"]
