import re

with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    c = f.read()
c = re.sub(r"const \[needsSelection, setNeedsSelection\] = useState\(false\);\n", "", c)
c = re.sub(r"setNeedsSelection\(true\);\n", "", c)
with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(c)

with open("frontend/src/pages/Landing.tsx", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("Shield, ChevronRight, GitBranch", "Shield, ChevronRight")
with open("frontend/src/pages/Landing.tsx", "w", encoding="utf-8") as f:
    f.write(c)

with open("frontend/src/pages/Login.tsx", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("Shield, GitBranch", "Shield")
with open("frontend/src/pages/Login.tsx", "w", encoding="utf-8") as f:
    f.write(c)

with open("frontend/src/pages/Register.tsx", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("Shield, GitBranch", "Shield")
with open("frontend/src/pages/Register.tsx", "w", encoding="utf-8") as f:
    f.write(c)

with open("frontend/src/pages/Onboarding.tsx", "r", encoding="utf-8") as f:
    c = f.read()
c = c.replace("GitBranch, CheckCircle2, ChevronRight, Loader2, GitFork, Shield, Search, AlertCircle, Lock, Globe", "GitBranch, CheckCircle2, Loader2, Shield, AlertCircle")
with open("frontend/src/pages/Onboarding.tsx", "w", encoding="utf-8") as f:
    f.write(c)
