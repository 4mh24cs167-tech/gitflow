with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("async def mock_get(url, *args, **kwargs):", "async def mock_get(self, url, *args, **kwargs):")

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
