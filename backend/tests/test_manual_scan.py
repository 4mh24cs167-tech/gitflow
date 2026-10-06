import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.api.routes.repositories import get_current_user
from app.database.models import User, Scan
from app.api.routes import repositories
from unittest.mock import AsyncMock

async def mock_get_current_user():
    return User(id=1, username="test_user")



@pytest.mark.asyncio
async def test_manual_scan_request_is_accepted(monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_current_user, mock_get_current_user)
    mock_queue = AsyncMock(return_value=(Scan(id=1, status="QUEUED"), True))
    monkeypatch.setattr(repositories, "owned_repository", AsyncMock())
    monkeypatch.setattr(repositories, "queue_scan", mock_queue)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/repositories/3/scan", json={"commit_sha": "HEAD"})

    assert response.status_code == 200
