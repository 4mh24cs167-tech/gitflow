with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import pytest\n", "import pytest\nfrom httpx import Request\n")
content = content.replace("return Response(200, json={", "return Response(200, request=Request('GET', url), json={")
content = content.replace("return Response(404)", "return Response(404, request=Request('GET', url))")

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
