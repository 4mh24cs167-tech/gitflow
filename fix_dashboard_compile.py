with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

if "const [needsSelection, setNeedsSelection] = useState(false);" not in content:
    content = content.replace("const [loading, setLoading] = useState(true);",
                              "const [loading, setLoading] = useState(true);\n  const [needsSelection, setNeedsSelection] = useState(false);")

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(content)
