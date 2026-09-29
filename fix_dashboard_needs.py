with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = re.sub(r"if \(needsSelection\) \{.*?return \(\s*<div className=\"max-w-6xl mx-auto py-12 text-center\">.*?</select>\s*</div>\s*\);\s*\}", "", content, flags=re.DOTALL)

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(content)
