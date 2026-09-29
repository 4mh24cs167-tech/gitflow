import os
import re

src_dir = 'frontend/src'

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith(('.tsx', '.ts')):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = content.replace("import { apiClient, API_URL } from", "import { apiClient } from")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
