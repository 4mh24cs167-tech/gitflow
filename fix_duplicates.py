import re

with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Strip out ALL instances of handleRepoChange
content = re.sub(r'\s*const handleRepoChange = \(e: any\) => \{[\s\S]*?\};\n', '\n', content)

# Inject it ONCE at the top
content = content.replace("const [needsSelection, setNeedsSelection] = useState(false);", 
                          "const [needsSelection, setNeedsSelection] = useState(false);\n\n  const handleRepoChange = (e: any) => {\n    localStorage.setItem('gitflow_active_repo', e.target.value);\n    window.location.reload();\n  };")

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(content)

with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
    rp_content = f.read()

rp_content = re.sub(r'\s*const handleRepoChange = \(e: any\) => \{[\s\S]*?\};\n', '\n', rp_content)

rp_content = rp_content.replace("const [needsSelection, setNeedsSelection] = useState(false);", 
                          "const [needsSelection, setNeedsSelection] = useState(false);\n\n  const handleRepoChange = (e: any) => {\n    localStorage.setItem('gitflow_active_repo', e.target.value);\n    window.location.reload();\n  };")

with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
    f.write(rp_content)
