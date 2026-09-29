import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.models import User, Repository, Scan, Commit, RiskScore
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.mark.asyncio
async def test_onboarding_scan_lifecycle_failed():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
        
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_user", email="test@test.com", is_active=True, hashed_password="pw")
        repo = Repository(id=1, owner_id=1, name="test_repo", url="https://github.com/test_repo")
        commit = Commit(id=1, repository_id=1, hash="abcdef1234567890")
        scan = Scan(id=1, commit_id=1, status="FAILED")
        db.add_all([user, repo, commit, scan])
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
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/repositories/1/scans/1")
        assert res.status_code == 200
        
        data = res.json()
        assert data["status"] == "FAILED"
        assert data["commit_sha"] == "abcdef1234567890"
        assert data["risk_score"] is None
        
    app.dependency_overrides.clear()

from httpx import Response

@pytest.mark.asyncio
async def test_repository_creation_deduplication(monkeypatch):
    async def mock_get(self, url, *args, **kwargs):
        from httpx import Request
        return Response(200, request=Request('GET', url), json={
            "full_name": "test/test_repo",
            "default_branch": "main",
            "private": False,
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z"
        })
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
        
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_user", email="test@test.com", is_active=True, hashed_password="pw")
        user2 = User(id=2, username="test_user2", email="test2@test.com", is_active=True, hashed_password="pw")
        repo = Repository(id=1, owner_id=1, name="test_repo", url="https://github.com/test/test_repo")
        db.add_all([user, user2, repo])
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
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create duplicate repository for user 1
        res = await client.post("/repositories/", json={"name": "test_repo_new_name", "url": "https://github.com/test/test_repo.git"})
        assert res.status_code == 200
        assert res.json()["id"] == 1
        assert res.json()["name"] == "test_repo" # Name should not change because it's returning the exact existing one

        # Switch user 2
        async def override_get_current_user2():
            return User(id=2, username="test_user2", is_active=True)
        app.dependency_overrides[get_current_user] = override_get_current_user2
        
        # User 2 creates same URL repo
        res2 = await client.post("/repositories/", json={"name": "test_repo_new_name", "url": "https://github.com/test/test_repo.git"})
        assert res2.status_code == 200
        assert res2.json()["id"] == 2 # New repository id created for user 2!
        assert res2.json()["name"] == "test/test_repo"

    app.dependency_overrides.clear()
