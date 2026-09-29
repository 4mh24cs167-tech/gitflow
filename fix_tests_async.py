with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("@pytest.fixture\nasync def override_deps():", "async def setup_deps():")
content = content.replace("async def test_create_public_repository(override_deps, monkeypatch):", "async def test_create_public_repository(monkeypatch):\n    await setup_deps()")
content = content.replace("async def test_create_private_repository(override_deps, monkeypatch):", "async def test_create_private_repository(monkeypatch):\n    await setup_deps()")
content = content.replace("async def test_initial_scan_resolves_head(override_deps, monkeypatch):", "async def test_initial_scan_resolves_head(monkeypatch):\n    await setup_deps()")
content = content.replace("    yield\n    app.dependency_overrides.clear()", "")

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
