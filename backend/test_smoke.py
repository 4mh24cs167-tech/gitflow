import asyncio
import os
import sys
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:Fm7P8s7umt4OqqWv@db.zrtplsfswxegtigdvery.supabase.co:5432/postgres"

from app.database.session import AsyncSessionLocal, engine
from app.database.models import User, Repository, Commit, Scan, Finding, RiskScore
from sqlalchemy import select

async def run_smoke_test():
    print("Starting smoke test on Supabase...")
    
    async with AsyncSessionLocal() as db:
        # Pre-cleanup in case previous test failed
        existing = (await db.execute(select(User).where(User.username == "smoke_user"))).scalars().first()
        if existing:
            await db.delete(existing)
            await db.commit()
            
        # Create user
        user = User(username="smoke_user", email="smoke@example.com", hashed_password="smoke_hash", github_access_token="gAAAAA...")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created user: {user.id}")
        
        # Create repository
        repo = Repository(name="smoke-repo", url="https://github.com/smoke/repo.git", owner_id=user.id)
        db.add(repo)
        await db.commit()
        await db.refresh(repo)
        print(f"Created repo: {repo.id}")
        
        # Create commit
        commit = Commit(hash="1234567890abcdef1234567890abcdef12345678", message="smoke test", repository_id=repo.id)
        db.add(commit)
        await db.commit()
        await db.refresh(commit)
        print(f"Created commit: {commit.id}")
        
        # Create scan
        scan = Scan(commit_id=commit.id, status="COMPLETED", completed_at=datetime.utcnow())
        db.add(scan)
        await db.commit()
        await db.refresh(scan)
        print(f"Created scan: {scan.id}")
        
        # Create risk score with score_delta
        score = RiskScore(scan_id=scan.id, score=85, score_delta=-5, details="{}")
        db.add(score)
        
        # Create findings
        finding = Finding(scan_id=scan.id, fingerprint="hash1", status="NEW", type="Secret", description="Test finding", file_path="test.py", severity="High")
        db.add(finding)
        
        await db.commit()
        print("Created score and finding")
        
        # Verify read
        read_scan = (await db.execute(select(Scan).where(Scan.id == scan.id))).scalars().first()
        read_score = (await db.execute(select(RiskScore).where(RiskScore.scan_id == scan.id))).scalars().first()
        
        if read_score and read_score.score_delta == -5:
            print("Successfully verified reading score_delta.")
        else:
            print("Failed to read score_delta.")
            sys.exit(1)
            
        print("Smoke test PASSED!")
        
        # Clean up
        print("Cleaning up test data...")
        await db.delete(user) # cascade will delete repo, commit, scan, finding, score
        await db.commit()
        print("Cleanup done.")
        
if __name__ == "__main__":
    asyncio.run(run_smoke_test())
