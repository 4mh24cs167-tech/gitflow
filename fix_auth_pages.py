import re

for filename in ["frontend/src/pages/Register.tsx", "frontend/src/pages/Login.tsx"]:
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Remove GitHub OAuth button
    content = re.sub(r"<a href=\{`/auth/github/login`\}.*?</a>\s*", "", content, flags=re.DOTALL)
    
    # Remove "Or sign up with email" / "Or sign in with username" separator
    content = re.sub(r"<div className=\"relative mb-6\">\s*<div className=\"absolute inset-0 flex items-center\">\s*<div className=\"w-full border-t border-border-light dark:border-border-dark\"></div>\s*</div>\s*<div className=\"relative flex justify-center text-xs\">\s*<span className=\"px-2 bg-surface-light dark:bg-surface-dark text-slate-500\">Or sign.*?</span>\s*</div>\s*</div>\s*", "", content, flags=re.DOTALL)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

with open("frontend/src/pages/Landing.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("Connect GitBranch <GitBranch className=\"ml-2 w-4 h-4\" />", "Start for free <ChevronRight className=\"ml-1 w-4 h-4\" />")

with open("frontend/src/pages/Landing.tsx", "w", encoding="utf-8") as f:
    f.write(content)
