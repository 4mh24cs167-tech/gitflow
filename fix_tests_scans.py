with open("backend/tests/test_public_repos.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("assert len(scans) > 0\n        assert scans[0][\"commit_sha\"]", "if isinstance(scans, dict): print('Dict:', scans)\n        else: print('List:', scans)\n        assert len(scans) > 0\n        assert scans[0][\"commit_sha\"]")

with open("backend/tests/test_public_repos.py", "w", encoding="utf-8") as f:
    f.write(content)
