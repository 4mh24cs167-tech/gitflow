import os
import re

src_dir = 'frontend/src'

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith(('.tsx', '.ts')):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use regex to strip anything like `, { withCredentials: true }`
            content = re.sub(r',\s*\{\s*withCredentials:\s*true\s*\}', '', content)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
