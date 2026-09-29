with open("backend/tests/test_onboarding_scan.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from app.api.dependencies import get_db", "from app.database.session import get_db")

with open("backend/tests/test_onboarding_scan.py", "w", encoding="utf-8") as f:
    f.write(content)
