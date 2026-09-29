with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(r"import respx\nfrom httpx import Response\n\n@pytest\.mark\.asyncio\n@respx\.mock\nasync def test_repository_creation_deduplication\(\):\n\s+respx\.get.*?\"updated_at\": \"2020-01-01T00:00:00Z\"\n\s+\}\)\)\n", 
"""from httpx import Response

@pytest.mark.asyncio
async def test_repository_creation_deduplication(monkeypatch):
    async def mock_get(self, url, *args, **kwargs):
        from httpx import Request
        return Response(200, request=Request('GET', url), json={
            "full_name": "test/test_repo",
            "default_branch": "main",
            "private": False,
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-01T00:00:00Z"
        })
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)
""", content, flags=re.DOTALL)

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
