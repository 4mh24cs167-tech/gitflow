with open('backend/app/api/routes/repositories.py', 'r', encoding='utf-8') as f:
    code = f.read()

target1 = 'selectinload(Scan.risk_score)).where(Commit.repository_id'
repl1 = 'selectinload(Scan.risk_score), selectinload(Scan.findings)).where(Commit.repository_id'

target2 = '\"commit_message\": s.commit.message,'
repl2 = '\"commit_message\": s.commit.message,\n            \"findings_count\": len(s.findings),'

code = code.replace(target1, repl1)
code = code.replace(target2, repl2)

with open('backend/app/api/routes/repositories.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
