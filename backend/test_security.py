import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.database.models import User
from app.auth.security import encrypt_token, decrypt_token
from app.config import settings
import httpx

async def test_encryption():
    print("Testing encryption...")
    plain_token = "gho_fake_token_12345"
    encrypted = encrypt_token(plain_token)
    assert encrypted != plain_token
    assert encrypted.startswith("gAAAAA")
    decrypted = decrypt_token(encrypted)
    assert decrypted == plain_token
    print("Encryption test PASSED")

async def test_migration():
    print("Testing migrations...")
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./sql_app.db"
    
    # We already ran alembic upgrade head in terminal.
    # Let's insert a test user and check it works
    engine = create_async_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        new_user = User(username="test_encrypt", email="enc@enc.com", hashed_password="pw", github_access_token=encrypt_token("gho_test_123"))
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        db_user = (await db.execute(select(User).where(User.username == "test_encrypt"))).scalars().first()
        assert db_user is not None
        assert db_user.github_access_token.startswith("gAAAAA")
        assert decrypt_token(db_user.github_access_token) == "gho_test_123"
        print("Migration and DB read/write PASSED")

if __name__ == "__main__":
    asyncio.run(test_encryption())
    asyncio.run(test_migration())
