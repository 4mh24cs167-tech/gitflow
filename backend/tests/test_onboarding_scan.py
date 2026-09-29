import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.models import User, Repository, Scan, Commit, RiskScore
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.mark.asyncio
async def test_onboarding_scan_lifecycle_failed():
    # Setup test DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        from app.database.models import Base
        await conn.run_sync(Base.metadata.create_all)
        
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create user, repo, commit, scan
    async with TestingSessionLocal() as db:
        user = User(id=1, username="test_user", email="test@test.com", is_active=True, hashed_password="pw")
        repo = Repository(id=1, owner_id=1, name="test_repo", url="http://github.com/test_repo")
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
        # Simulate the polling
        res = await client.get("/repositories/1/scans/1")
        assert res.status_code == 200
        
        data = res.json()
        assert data["status"] == "FAILED"
        assert data["commit_sha"] == "abcdef1234567890"
        # Score must be None because there's no RiskScore in DB
        assert data["risk_score"] is None
        
    app.dependency_overrides.clear()
