with open('frontend/src/pages/Dashboard.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

target = 'scanId: h.id,'
repl = 'scanId: h.id,\n               findingsCount: h.findings_count,'

code = code.replace(target, repl)

with open('frontend/src/pages/Dashboard.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
