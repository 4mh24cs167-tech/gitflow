import os
import re

src_dir = 'frontend/src'

def get_depth(filepath):
    rel = os.path.relpath(filepath, src_dir)
    return rel.count(os.sep)

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith(('.tsx', '.ts')) and file != 'config.ts':
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'import axios from \'axios\';' in content or 'import axios from \"axios\";' in content:
                depth = get_depth(filepath)
                if depth == 0:
                    import_path = './config'
                else:
                    import_path = '../' * depth + 'config'
                
                content = re.sub(r'import axios from [\'"]axios[\'"];', f'import {{ apiClient, API_URL }} from \'{import_path}\';', content)
                
                # If API_URL is declared locally in the file, remove it
                content = re.sub(r'const API_URL = [^;]+;\n?', '', content)
                
                # Replace axios.get, axios.post, etc with apiClient.get
                content = content.replace('axios.get(', 'apiClient.get(')
                content = content.replace('axios.post(', 'apiClient.post(')
                content = content.replace('axios.put(', 'apiClient.put(')
                content = content.replace('axios.delete(', 'apiClient.delete(')
                
                # Remove API_URL from apiClient calls because baseURL is set
                content = content.replace('\${API_URL}', '')
                content = content.replace('${API_URL}', '')
                content = content.replace('API_URL + ', '')
                
                # Remove { withCredentials: true }
                content = content.replace(', { withCredentials: true }', '')
                content = content.replace(', {\n          withCredentials: true\n        }', '')
                content = content.replace(', {\n              withCredentials: true\n            }', '')
                content = content.replace(', {\n               withCredentials: true\n             }', '')
                
                # Fix cases where { withCredentials: true } was the third arg to post, it might leave empty {}?
                # Actually piClient.post('/auth/login', { ... }) doesn't need a third arg.
                # If it was piClient.post('...', data, { withCredentials: true }), it will become piClient.post('...', data)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
