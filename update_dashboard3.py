with open('frontend/src/pages/Dashboard.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

target = '<p className=\"font-medium\">{history.length > 0 ? history[history.length - 1].score : \'N/A\'}</p>'
repl = '<p className=\"font-medium\">{history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : \'Unavailable\') : \'N/A\'}</p>'

code = code.replace(target, repl)

target2 = 'value: history.length > 0 ? history[history.length - 1].score : \'N/A\','
repl2 = 'value: history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : \'Unavailable\') : \'N/A\','

code = code.replace(target2, repl2)

with open('frontend/src/pages/Dashboard.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
