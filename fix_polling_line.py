with open("backend/app/workers/polling.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("while True:        url = ", "while True:\n        url = ")

with open("backend/app/workers/polling.py", "w", encoding="utf-8") as f:
    f.write(content)
