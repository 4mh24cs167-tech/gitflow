import re

with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace test_repository_creation_deduplication
old_test = """@pytest.mark.asyncio
async def test_repository_creation_deduplication():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")"""
new_test = """import respx
from httpx import Response

@pytest.mark.asyncio
@respx.mock
async def test_repository_creation_deduplication():
    respx.get("https://api.github.com/repos/test/test_repo").mock(return_value=Response(200, json={
        "full_name": "test/test_repo",
        "default_branch": "main",
        "private": False,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-01T00:00:00Z"
    }))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")"""

content = content.replace(old_test, new_test)

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
