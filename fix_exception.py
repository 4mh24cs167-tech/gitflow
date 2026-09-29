with open("backend/app/api/routes/repositories.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("except Exception as e:\n        raise HTTPException(status_code=503, detail=\"Failed to communicate with GitHub API\")", "except Exception as e:\n        import traceback\n        traceback.print_exc()\n        raise HTTPException(status_code=503, detail=f\"Failed to communicate with GitHub API: {str(e)}\")")

with open("backend/app/api/routes/repositories.py", "w", encoding="utf-8") as f:
    f.write(content)
