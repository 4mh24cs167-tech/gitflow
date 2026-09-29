with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("assert res_get.json()[\"commit_sha\"] ==", "print(res_get.json())\n            assert res_get.json()[\"commit_sha\"] ==")

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
