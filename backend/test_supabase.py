import asyncio
import os
import sys

# Set DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:Fm7P8s7umt4OqqWv@db.zrtplsfswxegtigdvery.supabase.co:5432/postgres"

from app.database.session import engine, Base
from app.database import models

async def test_connection():
    try:
        async with engine.begin() as conn:
            print("Connected to Supabase PostgreSQL successfully.")
    except Exception as e:
        print(f"Error connecting: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connection())
