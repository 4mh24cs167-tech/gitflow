import pytest
import subprocess
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.models import User, Repository
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()

async def setup_deps(github_access_token=None):
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
        return User(id=1, username="test_user", is_active=True, github_access_token=github_access_token)
        
    from app.database.session import get_db
    from app.api.routes.repositories import get_current_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.mark.asyncio
async def test_create_public_repository(monkeypatch):
    await setup_deps()
    def mock_run(command, **kwargs):
        assert "--symref" in command
        assert "owner/repo" in command[-2]
        return subprocess.CompletedProcess(command, 0, "ref: refs/heads/main\tHEAD\n" + "a" * 40 + "\tHEAD\n", "")
    monkeypatch.setattr(subprocess, "run", mock_run)

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
    def mock_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 128, "", "repository not found")
    monkeypatch.setattr(subprocess, "run", mock_run)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/privaterepo"})
        assert res.status_code == 400
        assert res.json()["detail"] == "Repository not found, is private, or requires authentication."


@pytest.mark.asyncio
async def test_authenticated_private_repository_stays_private(monkeypatch):
    await setup_deps(github_access_token="encrypted-token")
    from app.api.routes import repositories
    monkeypatch.setattr(repositories, "decrypt_token", lambda value: "test-github-token")
    calls = []

    def mock_run(command, **kwargs):
        calls.append((command, kwargs))
        if kwargs["env"].get("GIT_CONFIG_COUNT"):
            return subprocess.CompletedProcess(command, 0, "ref: refs/heads/main\tHEAD\n" + "b" * 40 + "\tHEAD\n", "")
        return subprocess.CompletedProcess(command, 128, "", "repository not found")

    monkeypatch.setattr(subprocess, "run", mock_run)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/", json={"name": "repo", "url": "https://github.com/owner/private-repo"})
        assert res.status_code == 200
        assert res.json()["is_public"] is False
        assert len(calls) == 2
        assert all("test-github-token" not in " ".join(call[0]) for call in calls)

@pytest.mark.asyncio
async def test_initial_scan_resolves_head(monkeypatch):
    await setup_deps(github_access_token="encrypted-token")
    from app.api.routes import repositories
    monkeypatch.setattr(repositories, "decrypt_token", lambda value: "test-github-token")
    scan_worker = AsyncMock()
    monkeypatch.setattr(repositories, "run_scan", scan_worker)
    resolved_sha = "1234567890123456789012345678901234567890"

    def mock_run(command, **kwargs):
        assert "test-github-token" not in " ".join(command)
        assert kwargs["env"].get("GIT_CONFIG_COUNT") == "1"
        return subprocess.CompletedProcess(command, 0, f"{resolved_sha}\tHEAD\n", "")
    monkeypatch.setattr(subprocess, "run", mock_run)

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
        assert scans[0]["commit_sha"] == resolved_sha
        scan_worker.assert_awaited_once()
