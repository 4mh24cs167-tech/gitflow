with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace mock_get logic
new_test = """@pytest.mark.asyncio
async def test_initial_scan_resolves_head(monkeypatch):
    await setup_deps()
    original_get = AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        if str(url).startswith("https://api.github.com"):
            return Response(200, request=Request('GET', url), json={
                "sha": "1234567890123456789012345678901234567890"
            })
        return await original_get(self, url, *args, **kwargs)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    from app.database.session import get_db
    async for db in app.dependency_overrides[get_db]():
        repo = Repository(id=1, owner_id=1, name="owner/repo", url="https://github.com/owner/repo")
        db.add(repo)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/repositories/1/scan", json={"commit_sha": "HEAD"})
        assert res.status_code == 200
        
        # `res.json()` from `POST /scan` returns `{ "scan_id": X, "status": "QUEUED" }`
        scan_id = res.json()["scan_id"]
        
        # We need to test the database directly or hit `/repositories/1/scans` (plural) which has commit_sha
        res_get = await client.get(f"/repositories/1/scans")
        assert res_get.status_code == 200
        scans = res_get.json()
        assert len(scans) > 0
        assert scans[0]["commit_sha"] == "1234567890123456789012345678901234567890"
"""

import re
content = re.sub(r"@pytest\.mark\.asyncio\nasync def test_initial_scan_resolves_head.*?1234567890\"", new_test, content, flags=re.DOTALL)

# Do the same for test_create_public_repository
content = re.sub(r"async def mock_get\(self, url, \*args, \*\*kwargs\):\n\s+if str\(url\) == \"https://api.github.com/repos/owner/repo\":", 
    "original_get = AsyncClient.get\n    async def mock_get(self, url, *args, **kwargs):\n        if str(url).startswith(\"https://api.github.com\"):\n            if str(url) == \"https://api.github.com/repos/owner/repo\":", content)

content = re.sub(r"return Response\(404, request=Request\('GET', url\)\)", 
    "return Response(404, request=Request('GET', url))\n        return await original_get(self, url, *args, **kwargs)", content)

# Do the same for test_create_private_repository
content = re.sub(r"async def test_create_private_repository\(monkeypatch\):\n    await setup_deps\(\)\n    async def mock_get\(self, url, \*args, \*\*kwargs\):",
    "async def test_create_private_repository(monkeypatch):\n    await setup_deps()\n    original_get = AsyncClient.get\n    async def mock_get(self, url, *args, **kwargs):\n        if str(url).startswith(\"https://api.github.com\"):", content)
content = re.sub(r"\"private\": True\n        }\)", "\"private\": True\n            })\n        return await original_get(self, url, *args, **kwargs)", content)


with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
