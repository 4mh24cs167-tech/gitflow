with open('backend/app/api/routes/repositories.py', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('\"time\": scan.commit', '\"timestamp\": scan.commit')
with open('backend/app/api/routes/repositories.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Replaced')
