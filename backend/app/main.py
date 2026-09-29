from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database.session import engine, Base
from app.api.routes import auth, repositories, webhooks, notifications
# import models to ensure they are registered with Base metadata
from app.database import models

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.workers.polling import repository_polling_loop
    task = asyncio.create_task(repository_polling_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
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

@app.get("/")
async def root():
    return {"message": "Welcome to Software Risk Passport API"}
