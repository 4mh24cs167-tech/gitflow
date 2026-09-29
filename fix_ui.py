import re

def rewrite_dashboard():
    with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Needs a complete rewrite of the fetch block
    content = re.sub(
        r'const \[activeRepoId, setActiveRepoId\] = useState<string \| null>\([^)]*\);',
        'const [activeRepoId, setActiveRepoId] = useState<string | null>(localStorage.getItem(\'gitflow_active_repo\'));\n  const [needsSelection, setNeedsSelection] = useState(false);',
        content
    )
    
    fetch_logic = """        const res = await apiClient.get(`/repositories/`);
        setRepos(res.data);
        
        if (res.data.length === 0) {
            setLoading(false);
            return;
        }
        
        let targetId = activeRepoId;
        if (!targetId || !res.data.find((r: any) => r.id.toString() === targetId)) {
            if (res.data.length === 1) {
                targetId = res.data[0].id.toString();
                setActiveRepoId(targetId);
                localStorage.setItem('gitflow_active_repo', targetId as string);
            } else {
                setNeedsSelection(true);
                setLoading(false);
                return;
            }
        }
        
        if (targetId) {
           const historyRes = await apiClient.get(`/repositories/${targetId}/risk-history`);
           const chartData = historyRes.data.map((h: any) => ({
             scanId: h.id,
             findingsCount: h.findings_count,
             repoId: targetId,
             commit: h.short_sha,
             score: h.risk_score,
             date: new Date(h.scanned_at).toLocaleDateString(),
             scoreDelta: h.score_delta,
             alerts: h.alerts
           }));
           setHistory(chartData);
        }"""
        
    # Replace the old fetch logic
    content = re.sub(r'const res = await apiClient\.get\(`/repositories/`\);.*?setHistory\(chartData\);\n\s*\}', fetch_logic, content, flags=re.DOTALL)
    
    # Add needsSelection to UI
    ui_logic = """  if (needsSelection) {
    return (
      <div className="max-w-6xl mx-auto py-12 text-center">
         <h2 className="text-2xl font-bold mb-4 text-slate-800 dark:text-white">Select a Repository</h2>
         <select 
           className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-4 py-2 text-base outline-none"
           onChange={handleRepoChange} 
           defaultValue=""
         >
           <option value="" disabled>Select a repository...</option>
           {repos.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
         </select>
       </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">"""
    
    content = content.replace('  return (\n    <div className="max-w-6xl mx-auto space-y-6 pb-12">', ui_logic)
    
    with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
        f.write(content)

def rewrite_passport():
    with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
        content = f.read()

    # Add needsSelection state
    content = content.replace('const [latestScan, setLatestScan] = useState<any>(null);',
                              'const [latestScan, setLatestScan] = useState<any>(null);\n  const [needsSelection, setNeedsSelection] = useState(false);')

    fetch_logic = """        // 1. Get repos
        const repoRes = await apiClient.get(`/repositories/`);
        setRepos(repoRes.data);
        if (repoRes.data.length === 0) {
          setLoading(false);
          return;
        }
        
        let targetId = localStorage.getItem('gitflow_active_repo');
        let activeRepo = repoRes.data.find((r: any) => r.id.toString() === targetId);
        
        if (!activeRepo) {
            if (repoRes.data.length === 1) {
                activeRepo = repoRes.data[0];
                localStorage.setItem('gitflow_active_repo', activeRepo.id.toString());
            } else {
                setNeedsSelection(true);
                setLoading(false);
                return;
            }
        }
        setRepo(activeRepo);"""
        
    content = re.sub(r'// 1\. Get repos.*?setRepo\(activeRepo\);\s*setRepos\(repoRes\.data\);', fetch_logic, content, flags=re.DOTALL)

    ui_logic = """  if (needsSelection) {
     return (
       <div className="max-w-6xl mx-auto py-12 text-center">
         <Shield className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-700 mb-4" />
         <h2 className="text-2xl font-bold mb-4 text-slate-800 dark:text-white">Select a Repository</h2>
         <select 
           className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-4 py-2 text-base outline-none"
           onChange={handleRepoChange} 
           defaultValue=""
         >
           <option value="" disabled>Select a repository...</option>
           {repos.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
         </select>
       </div>
     );
  }

  if (!repo || history.length === 0 || !latestScan) {"""

    content = content.replace('  if (!repo || history.length === 0 || !latestScan) {', ui_logic)
    
    with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
        f.write(content)

rewrite_dashboard()
rewrite_passport()
