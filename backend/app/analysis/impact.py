import subprocess
import re
import os
import json
from typing import Dict, List, Any

def run_git_command(repo_dir: str, command: List[str]) -> str:
    result = subprocess.run(command, cwd=repo_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Git command failed: {result.stderr}")
    return result.stdout

def analyze_commit_changes(repo_dir: str, current_sha: str) -> List[Dict[str, Any]]:
    try:
        parent_sha_output = run_git_command(repo_dir, ["git", "rev-parse", f"{current_sha}^"])
        parent_sha = parent_sha_output.strip()
    except Exception:
        parent_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    status_out = run_git_command(repo_dir, ["git", "diff-tree", "--no-commit-id", "--name-status", "-M", "-r", parent_sha, current_sha])
    numstat_out = run_git_command(repo_dir, ["git", "diff", "--numstat", parent_sha, current_sha])
    
    numstat = {}
    for line in numstat_out.strip().split('\n'):
        if not line: continue
        parts = line.split('\t')
        if len(parts) == 3:
            add, sub, path = parts
            numstat[path] = {'add': add, 'sub': sub}

    results = []
    
    # Get unified diff for patch extraction
    try:
        full_diff_out = run_git_command(repo_dir, ["git", "diff", "-U3", parent_sha, current_sha])
    except Exception:
        full_diff_out = ""
        
    # Simple regex to split patches by file
    import re
    diffs_by_file = {}
    if full_diff_out:
        # Split by 'diff --git '
        chunks = full_diff_out.split('\ndiff --git ')
        for i, chunk in enumerate(chunks):
            if i == 0 and not chunk.startswith('diff --git '): continue
            chunk_content = ('diff --git ' + chunk) if i > 0 else chunk
            # Find the b/ filename
            # e.g. diff --git a/file.txt b/file.txt
            lines = chunk_content.split('\n')
            if lines:
                m = re.match(r'^diff --git a/(.*?) b/(.*)$', lines[0])
                if m:
                    file_path = m.group(2)
                    # truncate huge diffs (e.g. > 1000 lines)
                    if len(lines) > 1000:
                        chunk_content = '\n'.join(lines[:1000]) + '\n... [Diff truncated due to size]'
                    diffs_by_file[file_path] = chunk_content
    
    for line in status_out.strip().split('\n'):
        if not line: continue
        parts = line.split('\t')
        status = parts[0]
        path = parts[1]
        old_path = None
        if len(parts) >= 3 and status.startswith('R'): 
            old_path = parts[1]
            path = parts[2]
            
        lang = os.path.splitext(path)[1]
        
        adds = numstat.get(path, {}).get('add', '0')
        subs = numstat.get(path, {}).get('sub', '0')
        
        patch = diffs_by_file.get(path, "")
        
        results.append({
            "file": path,
            "old_path": old_path,
            "status": status,
            "language": lang,
            "additions": adds,
            "deletions": subs,
            "patch": patch
        })
        
    return results

def analyze_structural_changes(repo_dir: str, current_sha: str) -> Dict[str, Any]:
    try:
        parent_sha_output = subprocess.run(["git", "rev-parse", f"{current_sha}^"], cwd=repo_dir, capture_output=True, text=True)
        if parent_sha_output.returncode != 0:
            parent_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        else:
            parent_sha = parent_sha_output.stdout.strip()
    except Exception:
        parent_sha = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
    diff_out = run_git_command(repo_dir, ["git", "diff", parent_sha, current_sha])
    
    added = []
    removed = []
    
    pattern = re.compile(r'^([+-])\s*(?:class|def|function)\s+([a-zA-Z0-9_]+)')
    for line in diff_out.split('\n'):
        match = pattern.match(line)
        if match:
            sign = match.group(1)
            name = match.group(2)
            if sign == '+':
                added.append(name)
            else:
                removed.append(name)
                
    return {
        "added_structures": added,
        "removed_structures": removed
    }

def build_dependency_graph(repo_dir: str) -> Dict[str, List[str]]:
    import_regex = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)|require\([\'"]([^\'"]+)[\'"]\)')
    graph = {}
    
    for root, _, files in os.walk(repo_dir):
        if '.git' in root: continue
            
        for file in files:
            if not file.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
                continue
                
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, repo_dir).replace('\\', '/')
            graph[rel_path] = []
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        match = import_regex.search(line)
                        if match:
                            mod = match.group(1) or match.group(2)
                            if mod:
                                graph[rel_path].append(mod)
            except Exception:
                pass
                
    reverse_graph = {}
    for f, imports in graph.items():
        if f not in reverse_graph:
            reverse_graph[f] = []
        for imp in imports:
            if imp not in reverse_graph:
                reverse_graph[imp] = []
            if f not in reverse_graph[imp]:
                reverse_graph[imp].append(f)
            
    return reverse_graph

def analyze_impact(changed_files: List[str], reverse_dependency_graph: Dict[str, List[str]]) -> Dict[str, Any]:
    impact = {}
    for cf in changed_files:
        base = os.path.splitext(os.path.basename(cf))[0]
        affected = reverse_dependency_graph.get(base, [])
        affected.extend(reverse_dependency_graph.get(cf, []))
        
        affected = list(set(affected))
        
        for aff in affected:
            review_priority = "LOW"
            if 'auth' in aff.lower() or 'security' in aff.lower():
                review_priority = "HIGH"
            elif 'shared' in aff.lower() or 'common' in aff.lower() or 'utils' in aff.lower():
                review_priority = "MEDIUM"
                
            if aff not in impact:
                impact[aff] = []
            impact[aff].append({"changed_file": cf, "review_priority": review_priority, "category": "POTENTIALLY AFFECTED"})
            
    return impact
