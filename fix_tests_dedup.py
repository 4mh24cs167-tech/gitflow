with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("url=\"https://github.com/test/test_repo.git\"", "url=\"https://github.com/test/test_repo\"")

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
