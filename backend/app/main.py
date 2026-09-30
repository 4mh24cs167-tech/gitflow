from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.session import engine, Base
from app.api.routes import auth, repositories, webhooks, notifications, admin
# import models to ensure they are registered with Base metadata
from app.database import models

import asyncio
import logging

logger = logging.getLogger(__name__)

def run_migrations():
    from alembic.config import Config
    from alembic import command
    # Assuming the working directory is backend
    import os
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    # Set the script location manually just in case
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic"))
    command.upgrade(alembic_cfg, "head")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(run_migrations)
        logger.info("Successfully ran database migrations.")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")

    yield
    await engine.dispose()

app = FastAPI(title="Software Risk Passport", lifespan=lifespan)

from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(webhooks.router)
app.include_router(notifications.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Software Risk Passport API"}
