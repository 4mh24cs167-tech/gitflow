import os
import re

files = [
    "frontend/src/pages/Dashboard.tsx",
    "frontend/src/pages/Onboarding.tsx",
    "frontend/src/pages/Login.tsx",
    "frontend/src/pages/Register.tsx"
]

for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    # Add import if missing
    if "import { API_URL } from '../config';" not in content and "${API_URL}" in content:
        content = "import { API_URL } from '../config';\n" + content
        
    # Replace single quoted '${API_URL}...' with backticks
    content = re.sub(r"'(\$\{API_URL\}[^']*)'", r"`\1`", content)
    
    # Replace double quoted "${API_URL}..." with backticks
    content = re.sub(r'"(\$\{API_URL\}[^"]*)"', r"`\1`", content)
    
    with open(file, "w") as f:
        f.write(content)
