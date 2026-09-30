import re
with open("backend/app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """import asyncio
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

    from app.workers.polling import repository_polling_loop
    task = asyncio.create_task(repository_polling_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
"""

# Find the lifespan function and replace it
content = re.sub(r"import asyncio.*?await engine\.dispose\(\)\n", replacement, content, flags=re.DOTALL)

with open("backend/app/main.py", "w", encoding="utf-8") as f:
    f.write(content)
