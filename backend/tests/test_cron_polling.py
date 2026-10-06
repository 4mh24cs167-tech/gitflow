import pytest
import os
import asyncio
import shutil
import subprocess
import stat
import uuid
from pathlib import Path
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.session import AsyncSessionLocal, engine, Base
from app.database.models import User, Repository, Commit, Scan
from app.config import settings

@pytest.fixture(autouse=True)
def override_settings():
    settings.CRON_SECRET = "test-secret"
    yield
    settings.CRON_SECRET = ""

@pytest.mark.asyncio
async def test_cron_authentication():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing secret
        res = await client.post("/admin/polling/run")
        assert res.status_code == 401
        
        # Valid secret
        res = await client.post("/admin/polling/run", headers={"Authorization": "Bearer test-secret"})
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_polling_errors_are_returned_as_a_failed_run(monkeypatch):
    from app.api.routes import admin
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    suffix = uuid4().hex
    async with AsyncSessionLocal() as db:
        user = User(username=f"poll-{suffix}", email=f"poll-{suffix}@example.invalid", hashed_password="test")
        db.add(user)
        await db.flush()
        db.add(Repository(
            name="poll-test", url="https://github.com/example/poll-test", owner_id=user.id,
            monitoring_status="POLLING_ACTIVE",
        ))
        await db.commit()

    async def failed_repository_poll(repo_id, semaphore, deadline):
        return {"repo_id": repo_id, "changed": False, "commits_discovered": 0, "commits_queued": 0, "error": "test failure", "partial": False}

    monkeypatch.setattr(admin, "process_one_repository", failed_repository_poll)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/admin/polling/run", headers={"Authorization": "Bearer test-secret"})
    assert response.status_code == 503
    assert response.json()["status"] == "completed_with_errors"
    assert response.json()["errors"] >= 1

def _make_local_repository(root: Path) -> tuple[Path, list[str]]:
    """Make an isolated history inside the project; never use a network remote."""
    worktree = root / "source"
    worktree.mkdir(parents=True)
    env = os.environ.copy()
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})
    subprocess.run(["git", "init", "-b", "main", str(worktree)], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(worktree), "config", "user.name", "Gitflow Test"], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(worktree), "config", "user.email", "gitflow-test@example.invalid"], check=True, capture_output=True, env=env)
    shas = []
    for index in range(1, 6):
        (worktree / "history.txt").write_text(f"revision {index}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(worktree), "add", "history.txt"], check=True, capture_output=True, env=env)
        subprocess.run(["git", "-C", str(worktree), "commit", "-m", f"msg {index}"], check=True, capture_output=True, env=env)
        shas.append(subprocess.run(["git", "-C", str(worktree), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=env).stdout.strip())
    return worktree, shas


def _remove_local_repository(root: Path) -> None:
    def retry_readonly_file(function, path, _error):
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        function(path)

    shutil.rmtree(root, onerror=retry_readonly_file)


def _use_local_clone_source(monkeypatch, local_source: Path) -> None:
    from app.api.routes import admin
    real_create_subprocess_exec = asyncio.create_subprocess_exec

    async def create_subprocess_exec(*args, **kwargs):
        command = list(args)
        if command[:2] == ["git", "clone"]:
            command[-2] = str(local_source)
        return await real_create_subprocess_exec(*command, **kwargs)

    monkeypatch.setattr(admin.asyncio, "create_subprocess_exec", create_subprocess_exec)


@pytest.mark.asyncio
async def test_git_polling_returns_bounded_commits_oldest_first(monkeypatch):
    from app.api.routes.admin import fetch_missing_commits
    root = Path(__file__).resolve().parent / f".git-poll-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        local_source, shas = _make_local_repository(root)
        _use_local_clone_source(monkeypatch, local_source)
        bare_repo_dir = str(root / "bare-first")

        result = await fetch_missing_commits("owner", "repo", "main", shas[1], max_commits=2, bare_repo_dir=bare_repo_dir)
        assert result["status"] == "success"
        assert [commit["sha"] for commit in result["commits"]] == shas[2:4]
        assert [commit["message"] for commit in result["commits"]] == ["msg 3", "msg 4"]

        result = await fetch_missing_commits("owner", "repo", "main", shas[3], max_commits=2, bare_repo_dir=str(root / "bare-second"))
        assert result["status"] == "success"
        assert [commit["sha"] for commit in result["commits"]] == shas[4:]
    finally:
        _remove_local_repository(root)

@pytest.mark.asyncio
async def test_git_polling_reports_missing_anchor(monkeypatch):
    from app.api.routes.admin import fetch_missing_commits
    root = Path(__file__).resolve().parent / f".git-poll-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        local_source, _ = _make_local_repository(root)
        _use_local_clone_source(monkeypatch, local_source)
        result = await fetch_missing_commits("owner", "repo", "main", "0" * 40, max_commits=10, bare_repo_dir=str(root / "bare"))
        assert result["status"] == "anchor_not_found"
        assert result["commits"] == []
    finally:
        _remove_local_repository(root)

@pytest.mark.asyncio
async def test_git_clone_errors_are_reported_without_raw_output(monkeypatch):
    from app.api.routes.admin import fetch_missing_commits
    root = Path(__file__).resolve().parent / f".git-poll-{uuid.uuid4().hex}"
    root.mkdir()
    try:
        _use_local_clone_source(monkeypatch, root / "does-not-exist")
        result = await fetch_missing_commits("owner", "repo", "main", None, max_commits=10, bare_repo_dir=str(root / "bare"))
        assert result["status"] == "api_error"
        assert result["commits"] == []
    finally:
        _remove_local_repository(root)
