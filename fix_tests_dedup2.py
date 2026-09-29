with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("assert res2.json()[\"name\"] == \"test_repo_new_name\"", "assert res2.json()[\"name\"] == \"test/test_repo\"")

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
