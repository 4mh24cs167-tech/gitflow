with open('frontend/src/pages/Dashboard.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

target = 'const [history, setHistory] = useState<{ commit: string; score: number; date: string; scoreDelta: number | null }[]>([]);'
repl = 'const [history, setHistory] = useState<{ commit: string; score: number | null; date: string; scoreDelta: number | null; findingsCount?: number }[]>([]);'

code = code.replace(target, repl)

with open('frontend/src/pages/Dashboard.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
print('SUCCESS')
