with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace('https://github.com/test/test_repo', 'https://github.com/test/test_repo.git')
content = content.replace('if res.status_code != 200: print(res.json()); assert False', 'assert res.status_code == 200')

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
