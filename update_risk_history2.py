with open('backend/app/api/routes/repositories.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('\"risk_score\": s.risk_score.score if s.risk_score else 100,', '\"risk_score\": s.risk_score.score if s.risk_score else None,')

with open('backend/app/api/routes/repositories.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
