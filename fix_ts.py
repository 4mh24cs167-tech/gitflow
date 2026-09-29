with open("frontend/src/pages/Onboarding.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("const [repos, setRepos] = useState([]);", "const [repos, setRepos] = useState<any[]>([]);")
content = content.replace("const [scanId, setScanId] = useState<number | null>(null);", "")
content = content.replace("setScanId(newScanId);", "")

with open("frontend/src/pages/Onboarding.tsx", "w", encoding="utf-8") as f:
    f.write(content)
