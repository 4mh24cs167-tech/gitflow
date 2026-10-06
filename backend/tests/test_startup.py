import pytest

from app import main


@pytest.mark.asyncio
async def test_startup_stops_if_database_migrations_fail(monkeypatch):
    disposed = False

    def fail_migrations():
        raise RuntimeError("migration failed")

    class FakeEngine:
        async def dispose(self):
            nonlocal disposed
            disposed = True

    monkeypatch.setattr(main, "run_migrations", fail_migrations)
    monkeypatch.setattr(main, "engine", FakeEngine())

    with pytest.raises(RuntimeError, match="migration failed"):
        async with main.lifespan(main.app):
            pytest.fail("the application must not start when migrations fail")

    assert disposed
