import pytest
import os
import json
import httpx
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
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
        
        # Valid secret
        res = await client.post("/admin/polling/run", headers={"Authorization": "Bearer test-secret"})
        assert res.status_code == 200

@pytest.mark.asyncio
async def test_pagination_and_anchor_discovery():
    """TEST 1 & TEST 2: Pagination correctly identifies exact missing range and processes oldest->newest."""
    from app.api.routes.admin import fetch_missing_commits
    
    all_commits = [{"sha": f"{i}", "commit": {"message": f"msg {i}"}} for i in range(60, 0, -1)]
    
    async def mock_get(url, headers):
        page = int(url.split("page=")[-1])
        start = (page - 1) * 30
        end = start + 30
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: all_commits[start:end]
        return mock_response

    with patch('httpx.AsyncClient.get', side_effect=mock_get):
        res = await fetch_missing_commits("owner", "repo", "main", "40", max_commits=10)
        assert res["status"] == "success"
        assert len(res["commits"]) == 10
        assert [c["sha"] for c in res["commits"]] == [f"{i}" for i in range(41, 51)]
        
        res = await fetch_missing_commits("owner", "repo", "main", "50", max_commits=10)
        assert res["status"] == "success"
        assert len(res["commits"]) == 10
        assert [c["sha"] for c in res["commits"]] == [f"{i}" for i in range(51, 61)]

@pytest.mark.asyncio
async def test_anchor_not_found():
    """TEST 3 & TEST 10: Anchor missing yields ANCHOR_NOT_FOUND."""
    from app.api.routes.admin import fetch_missing_commits
    
    async def mock_get(url, headers):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: [] # end of history
        return mock_response

    with patch('httpx.AsyncClient.get', side_effect=mock_get):
        res = await fetch_missing_commits("owner", "repo", "main", "MISSING_SHA", max_commits=10)
        assert res["status"] == "anchor_not_found"

@pytest.mark.asyncio
async def test_api_errors():
    """TEST 4 & TEST 5: API returns 403 or 429 -> RATE_LIMITED."""
    from app.api.routes.admin import fetch_missing_commits
    
    async def mock_get(url, headers):
        mock_response = AsyncMock()
        mock_response.status_code = 403
        return mock_response

    with patch('httpx.AsyncClient.get', side_effect=mock_get):
        res = await fetch_missing_commits("owner", "repo", "main", "40", max_commits=10)
        assert res["status"] == "rate_limited"
