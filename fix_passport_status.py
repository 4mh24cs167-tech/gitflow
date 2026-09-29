with open("frontend/src/pages/RiskPassport.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace missing score logic
old_score = "{risk_score !== null ? risk_score : 'N/A'}"
new_score = "{status === 'FAILED' ? 'SCAN FAILED' : risk_score !== null ? risk_score : 'UNAVAILABLE'}"
content = content.replace(old_score, new_score)

# Replace 'N/A' in Dashboard just to be safe
with open("frontend/src/pages/Dashboard.tsx", "r", encoding="utf-8") as f:
    dashboard_content = f.read()

dashboard_content = dashboard_content.replace("'Unavailable') : 'N/A'", "'Unavailable') : 'NO COMPLETED SCAN'")

with open("frontend/src/pages/RiskPassport.tsx", "w", encoding="utf-8") as f:
    f.write(content)

with open("frontend/src/pages/Dashboard.tsx", "w", encoding="utf-8") as f:
    f.write(dashboard_content)
