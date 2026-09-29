with open("backend/app/api/routes/repositories.py", "r", encoding="utf-8") as f:
    content = f.read()

old_return = 'return [{"id": r["id"], "name": r["full_name"], "url": r["clone_url"], "language": r.get("language")} for r in response.json()]'
new_return = 'return [{"id": r["id"], "name": r["full_name"], "url": r["clone_url"], "language": r.get("language"), "updated_at": r.get("updated_at"), "created_at": r.get("created_at"), "default_branch": r.get("default_branch"), "private": r.get("private")} for r in response.json()]'

content = content.replace(old_return, new_return)

with open("backend/app/api/routes/repositories.py", "w", encoding="utf-8") as f:
    f.write(content)
