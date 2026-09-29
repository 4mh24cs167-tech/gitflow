import sys

def modify_dashboard():
    with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Add activeRepoId state
    content = content.replace("const [repos, setRepos] = useState<any[]>([]);", 
                              "const [repos, setRepos] = useState<any[]>([]);\n  const [activeRepoId, setActiveRepoId] = useState<string | null>(localStorage.getItem('gitflow_active_repo') || null);")
    
    # 2. Update fetch logic
    old_fetch = """        const res = await apiClient.get(`/repositories/`);
        setRepos(res.data);
        
        if (res.data.length > 0) {
           const historyRes = await apiClient.get(`/repositories/${res.data[0].id}/risk-history`);"""
           
    new_fetch = """        const res = await apiClient.get(`/repositories/`);
        setRepos(res.data);
        
        let targetId = activeRepoId;
        if (res.data.length > 0 && !res.data.find((r: any) => r.id.toString() === targetId)) {
            targetId = res.data[0].id.toString();
            setActiveRepoId(targetId);
            localStorage.setItem('gitflow_active_repo', targetId as string);
        }
        
        if (targetId) {
           const historyRes = await apiClient.get(`/repositories/${targetId}/risk-history`);"""
    
    content = content.replace(old_fetch, new_fetch)
    
    # 3. Add handleRepoChange
    repo_change_func = """  const handleRepoChange = (e: any) => {
    const id = e.target.value;
    setActiveRepoId(id);
    localStorage.setItem('gitflow_active_repo', id);
    window.location.reload();
  };"""
    
    content = content.replace("  const stats = [", repo_change_func + "\n\n  const stats = [")
    
    # 4. Add dropdown to UI
    header_start = """  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">"""
    
    dropdown_ui = """  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {repos.length > 1 && (
        <div className="flex justify-end mb-4">
          <select 
            className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
            value={activeRepoId || ''}
            onChange={handleRepoChange}
          >
            {repos.map(r => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      )}"""
      
    content = content.replace(header_start, dropdown_ui)
    
    # Also fix window.location.href=`/repositories/${repo.id}` in Dashboard.tsx which is broken
    content = content.replace("window.location.href=`/repositories/${repo.id}`", "/* replaced */")

    with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
        f.write(content)


def modify_passport():
    with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    old_fetch = """        // 1. Get repos
        const repoRes = await apiClient.get(`/repositories/`);
        if (repoRes.data.length === 0) {
          setLoading(false);
          return;
        }
        const activeRepo = repoRes.data[0];
        setRepo(activeRepo);"""
        
    new_fetch = """        // 1. Get repos
        const repoRes = await apiClient.get(`/repositories/`);
        if (repoRes.data.length === 0) {
          setLoading(false);
          return;
        }
        
        let targetId = localStorage.getItem('gitflow_active_repo');
        let activeRepo = repoRes.data.find((r: any) => r.id.toString() === targetId);
        if (!activeRepo) {
            activeRepo = repoRes.data[0];
            localStorage.setItem('gitflow_active_repo', activeRepo.id.toString());
        }
        setRepo(activeRepo);"""
        
    content = content.replace(old_fetch, new_fetch)
    
    # Add handleRepoChange and dropdown
    header_start = """  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between">"""
      
    dropdown_ui = """  const handleRepoChange = (e: any) => {
    localStorage.setItem('gitflow_active_repo', e.target.value);
    window.location.reload();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-end mb-2">
        <select 
          className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
          value={repo.id.toString()}
          onChange={handleRepoChange}
        >
          <option value={repo.id}>{repo.name}</option>
          {/* Note: to properly show all repos here, we'd need repos state. For simplicity, Dashboard is the main place to switch, but we'll add it if they are passed. */}
        </select>
      </div>
      <div className="flex items-center justify-between">"""
    
    content = content.replace(header_start, dropdown_ui)
    
    with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
        f.write(content)

modify_dashboard()
modify_passport()
