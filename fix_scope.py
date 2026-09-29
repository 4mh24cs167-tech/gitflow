with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
    content = f.read()

handle_func = """  const handleRepoChange = (e: any) => {
    localStorage.setItem('gitflow_active_repo', e.target.value);
    window.location.reload();
  };"""

content = content.replace(handle_func, "")
content = content.replace("const [latestScan, setLatestScan] = useState<any>(null);\n  const [needsSelection, setNeedsSelection] = useState(false);", 
                          "const [latestScan, setLatestScan] = useState<any>(null);\n  const [needsSelection, setNeedsSelection] = useState(false);\n\n" + handle_func)

with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
    f.write(content)

with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    db_content = f.read()

db_content = db_content.replace(handle_func, "")
db_content = db_content.replace("const [loading, setLoading] = useState(true);\n  const [needsSelection, setNeedsSelection] = useState(false);",
                                "const [loading, setLoading] = useState(true);\n  const [needsSelection, setNeedsSelection] = useState(false);\n\n" + handle_func)

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(db_content)

