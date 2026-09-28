with open('frontend/src/pages/CommitAudit.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

target1 = '''  const prevScore = data.previous_score ?? 100;
  const currentScore = data.current_score ?? data.risk_score ?? prevScore;
  const delta = data.score_delta ?? (currentScore - prevScore);'''

repl1 = '''  const currentScore = data.risk_score;
  const prevScore = data.previous_score;
  const delta = data.score_delta;'''

target2 = '<span className=\"text-4xl font-bold text-slate-800 dark:text-white\">{currentScore}</span>'
repl2 = '<span className=\"text-4xl font-bold text-slate-800 dark:text-white\">{currentScore !== null ? currentScore : \"N/A\"}</span>'

target3 = '{delta !== 0 ? Math.abs(delta) : \'No change\'}'
repl3 = '{delta !== null && delta !== 0 ? Math.abs(delta) : delta === 0 ? \'No change\' : \'\'}'

target4 = '{delta < 0 ? <ArrowUpRight className=\"w-4 h-4 mr-1\" /> : delta > 0 ? <ArrowDownRight className=\"w-4 h-4 mr-1\" /> : null}'
repl4 = '{delta !== null && delta < 0 ? <ArrowUpRight className=\"w-4 h-4 mr-1\" /> : delta !== null && delta > 0 ? <ArrowDownRight className=\"w-4 h-4 mr-1\" /> : null}'

code = code.replace(target1, repl1)
code = code.replace(target2, repl2)
code = code.replace(target3, repl3)
code = code.replace(target4, repl4)

with open('frontend/src/pages/CommitAudit.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
