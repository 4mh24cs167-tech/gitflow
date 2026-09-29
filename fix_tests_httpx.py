import re

with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace respx with monkeypatch
content = content.replace("import respx\n", "")
content = content.replace("@respx.mock\n", "")

old_test1 = """async def test_create_public_repository(override_deps):
    respx.get("https://api.github.com/repos/owner/repo").mock(return_value=Response(200, json={
        "full_name": "owner/repo",
        "default_branch": "main",
        "private": False,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z"
    }))"""
new_test1 = """async def test_create_public_repository(override_deps, monkeypatch):
    async def mock_get(url, *args, **kwargs):
        if str(url) == "https://api.github.com/repos/owner/repo":
            return Response(200, json={
                "full_name": "owner/repo",
                "default_branch": "main",
                "private": False,
                "created_at": "2020-01-01T00:00:00Z",
                "updated_at": "2020-01-01T00:00:00Z"
            })
        return Response(404)
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)"""
content = content.replace(old_test1, new_test1)

old_test2 = """async def test_create_private_repository(override_deps):
    respx.get("https://api.github.com/repos/owner/privaterepo").mock(return_value=Response(200, json={
        "full_name": "owner/privaterepo",
        "default_branch": "main",
        "private": True
    }))"""
new_test2 = """async def test_create_private_repository(override_deps, monkeypatch):
    async def mock_get(url, *args, **kwargs):
        return Response(200, json={
            "full_name": "owner/privaterepo",
            "default_branch": "main",
            "private": True
        })
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)"""
content = content.replace(old_test2, new_test2)

old_test3 = """async def test_initial_scan_resolves_head(override_deps):
    respx.get("https://api.github.com/repos/owner/repo/commits/HEAD").mock(return_value=Response(200, json={
        "sha": "1234567890123456789012345678901234567890"
    }))"""
new_test3 = """async def test_initial_scan_resolves_head(override_deps, monkeypatch):
    async def mock_get(url, *args, **kwargs):
        return Response(200, json={
            "sha": "1234567890123456789012345678901234567890"
        })
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)"""
content = content.replace(old_test3, new_test3)

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
