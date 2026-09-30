import pytest
import os
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal, engine, Base
from app.database.models import User, Repository, Commit, Scan
from app.config import settings

@pytest.fixture(autouse=True)
def override_settings():
    settings.CRON_SECRET = "test-secret"
    yield
    settings.CRON_SECRET = ""

@pytest.mark.asyncio
async def test_cron_authentication():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing secret
        res = await client.post("/admin/polling/run")
        assert res.status_code == 401
        
        # Invalid secret
        res = await client.post("/admin/polling/run", headers={"Authorization": "Bearer bad-secret"})
        assert res.status_code == 401
        
        # Valid secret
        res = await client.post("/admin/polling/run", headers={"Authorization": "Bearer test-secret"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("completed", "skipped")
