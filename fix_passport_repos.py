with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("const [repo, setRepo] = useState<any>(null);", 
                          "const [repo, setRepo] = useState<any>(null);\n  const [repos, setRepos] = useState<any[]>([]);")

content = content.replace("setRepo(activeRepo);", "setRepo(activeRepo);\n        setRepos(repoRes.data);")

dropdown_old = """        <select 
          className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
          value={repo.id.toString()}
          onChange={handleRepoChange}
        >
          <option value={repo.id}>{repo.name}</option>
          {/* Note: to properly show all repos here, we'd need repos state. For simplicity, Dashboard is the main place to switch, but we'll add it if they are passed. */}
        </select>"""

dropdown_new = """        {repos.length > 1 && (
          <select 
            className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
            value={repo.id.toString()}
            onChange={handleRepoChange}
          >
            {repos.map((r: any) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        )}"""

content = content.replace(dropdown_old, dropdown_new)

with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
    f.write(content)
