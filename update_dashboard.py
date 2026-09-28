with open('frontend/src/pages/Dashboard.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

target = '<p className=\"font-medium\">N/A</p>'
replacement = '<p className=\"font-medium\">{history.length > 0 ? history[history.length - 1].findingsCount !== undefined ? history[history.length - 1].findingsCount : \"0\" : \"N/A\"}</p>'
if target in code:
    code = code.replace(target, replacement)
    with open('frontend/src/pages/Dashboard.tsx', 'w', encoding='utf-8') as f:
        f.write(code)
    print('SUCCESS')
else:
    print('NOT FOUND')
