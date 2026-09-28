import re

with open('backend/app/api/routes/repositories.py', 'r', encoding='utf-8') as f:
    code = f.read()

pattern = r'(\s+changes = \[\]\s+if analysis and analysis\.changed_files:\s+changes = json\.loads\(analysis\.changed_files\))(.*?)(return \{\s+"id": scan\.id,\s+"commit_sha": scan\.commit\.hash,)'

def repl(m):
    impact_code = '''
    impact = {}
    if analysis and analysis.impact_analysis:
        impact = json.loads(analysis.impact_analysis)'''
    
    ret = m.group(1) + impact_code + m.group(2) + '''return {
        "id": scan.id,
        "commit_sha": scan.commit.hash,
        "message": scan.commit.message,
        "author": scan.commit.author_name or "Unknown",
        "time": scan.commit.committed_at.isoformat() if scan.commit.committed_at else None,'''
    return ret

new_code, num = re.subn(pattern, repl, code, flags=re.DOTALL)
if num > 0:
    new_code = new_code.replace('"changes": changes,', '"changes": changes,\n        "impact": impact,')
    with open('backend/app/api/routes/repositories.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print('SUCCESS')
else:
    print('NOT FOUND')
