with open("backend/app/api/routes/repositories.py", "r", encoding="utf-8") as f:
    for line in f:
        if "findings\":" in line:
            print(line.strip())
