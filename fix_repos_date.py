with open("backend/app/api/routes/repositories.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from dateutil.parser import parse as parse_date", "from datetime import datetime\ndef parse_date(d: str):\n    return datetime.fromisoformat(d.replace('Z', '+00:00'))")

with open("backend/app/api/routes/repositories.py", "w", encoding="utf-8") as f:
    f.write(content)
