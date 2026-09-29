with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace header
old_header = """<div className="max-w-6xl mx-auto space-y-6 pb-12">"""
new_header = """<div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-between items-center mb-6 pt-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button onClick={() => window.location.href = '/onboarding'} className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors shadow-sm font-medium">
           + Add Repository
        </button>
      </div>"""
content = content.replace(old_header, new_header)

# Replace the active repo dropdown
import re
content = re.sub(r"\{repos\.length > 1 && \(\s*<div className=\"flex justify-end mb-4\">.*?</select>\s*</div>\s*\)\}", "", content, flags=re.DOTALL)

# Replace the Active Repositories grid columns
old_grid = """<div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border-light dark:border-border-dark">"""
new_grid = """<div className="grid grid-cols-2 md:grid-cols-6 gap-4 pt-4 border-t border-border-light dark:border-border-dark">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Owner</p>
                    <p className="font-medium truncate">{repo.github_owner || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Visibility</p>
                    <p className="font-medium">{repo.is_public ? 'Public' : 'Private'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Default Branch</p>
                    <p className="font-medium truncate">{repo.default_branch || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Last Updated</p>
                    <p className="font-medium text-sm truncate">{repo.github_updated_at ? new Date(repo.github_updated_at).toLocaleDateString() : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Monitoring</p>
                    <p className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center">
                      {repo.monitoring_enabled ? <><span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span> Active</> : 'Inactive'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Current Risk Score</p>
                    <p className="font-medium">{activeRepoId === repo.id.toString() && history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : 'Unavailable') : 'Select to view'}</p>
                  </div>
"""

content = content.replace(old_grid + """
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Monitoring Status</p>
                    <p className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center"><span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span> Active</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Current Risk Score</p>
                    <p className="font-medium">{history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : 'Unavailable') : 'NO COMPLETED SCAN'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Latest Commit</p>
                    <p className="font-medium truncate max-w-[120px]">{history.length > 0 ? history[history.length - 1].commit : 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Open Findings</p>
                    <p className="font-medium">{history.length > 0 ? history[history.length - 1].findingsCount !== undefined ? history[history.length - 1].findingsCount : "0" : "N/A"}</p>
                  </div>
""", new_grid)

# Add highlighting for active repo
old_card = """<div key={repo.id} className="px-6 py-6 flex flex-col space-y-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">"""
new_card = """<div key={repo.id} className={`px-6 py-6 flex flex-col space-y-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer ${activeRepoId === repo.id.toString() ? 'border-l-4 border-brand-500 bg-slate-50/50 dark:bg-slate-800/30' : ''}`} onClick={() => handleRepoChange({target: {value: repo.id.toString()}})}>"""
content = content.replace(old_card, new_card)

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(content)
