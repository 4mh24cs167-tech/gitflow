import pytest
from httpx import Response, AsyncClient, ASGITransport, Request
from app.main import app
from app.database.models import User, Repository
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def setup_deps():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
        
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_user", email="test@test.com", is_active=True, hashed_password="pw")
        db.add(user)
        await db.commit()
        
    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db
            
    async def override_get_current_user():
        return User(id=1, username="test_user", is_active=True)
        
    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.mark.asyncio
async def test_create_public_repository(monkeypatch):
    await setup_deps()
    original_get = AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        if str(url).startswith("https://api.github.com"):
            if str(url) == "https://api.github.com/repos/owner/repo":
                return Response(200, request=Request('GET', url), json={
                    "full_name": "owner/repo",
                    "default_branch": "main",
                    "private": False,
                    "created_at": "2020-01-01T00:00:00Z",
                    "updated_at": "2020-01-01T00:00:00Z"
                })
            return Response(404, request=Request('GET', url))
        return await original_get(self, url, *args, **kwargs)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/repo"})
        assert res.status_code == 200
        assert res.json()["name"] == "owner/repo"
        assert res.json()["url"] == "https://github.com/owner/repo"
        assert res.json()["is_public"] is True

        res = await client.post("/repositories/", json={"name": "repo", "url": "http://github.com/owner/repo"})
        assert res.status_code == 422
        
        res = await client.post("/repositories/", json={"name": "repo", "url": "git://github.com/owner/repo"})
        assert res.status_code == 422
        
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/repo?test=1"})
        assert res.status_code == 422
        
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/repo#frag"})
        assert res.status_code == 422

@pytest.mark.asyncio
async def test_create_private_repository(monkeypatch):
    await setup_deps()
    original_get = AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        if str(url).startswith("https://api.github.com"):
            return Response(200, request=Request('GET', url), json={
                "full_name": "owner/privaterepo",
                "default_branch": "main",
                "private": True
            })
        return await original_get(self, url, *args, **kwargs)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/privaterepo"})
        assert res.status_code == 400
        assert "This repository is private" in res.json()["detail"]

@pytest.mark.asyncio
async def test_initial_scan_resolves_head(monkeypatch):
    await setup_deps()
    original_get = AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        if str(url).startswith("https://api.github.com"):
            return Response(200, request=Request('GET', url), json={
                "sha": "1234567890123456789012345678901234567890"
            })
        return await original_get(self, url, *args, **kwargs)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    from app.database.session import get_db
    async for db in app.dependency_overrides[get_db]():
        repo = Repository(id=1, owner_id=1, name="owner/repo", url="https://github.com/owner/repo")
        db.add(repo)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/1/scan", json={"commit_sha": "HEAD"})
        assert res.status_code == 200
        
        res_get = await client.get("/repositories/1/scans")
        assert res_get.status_code == 200
        scans = res_get.json()
        assert len(scans) > 0
        assert scans[0]["commit_sha"] == "1234567890123456789012345678901234567890"
