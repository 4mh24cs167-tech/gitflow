import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

async def request(method, path, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, **kwargs)

@pytest.mark.asyncio
async def test_missing_auth():
    response = await request("GET", "/repositories/")
    assert response.status_code == 401
    
@pytest.mark.asyncio
async def test_invalid_auth():
    response = await request("GET", "/repositories/", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_ask_auth():
    response = await request("POST", "/repositories/1/scans/1/ask", json={"question": "What changed?"}, headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_missing_ask_auth():
    response = await request("POST", "/repositories/1/scans/1/ask", json={"question": "What changed?"})
    assert response.status_code == 401
