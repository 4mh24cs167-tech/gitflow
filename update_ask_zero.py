with open('backend/app/api/routes/repositories.py', 'r', encoding='utf-8') as f:
    code = f.read()

target = '''    elif matched_intent == "why_risk":
        score_delta = scan.risk_score.score_delta if scan.risk_score else 0
        current_score = scan.risk_score.score if scan.risk_score else 0
        previous_score = current_score - score_delta
        
        if score_delta == 0:
            answer = f"VERIFIED FACT:\\nThe risk score did not change (remained at {current_score})."
        else:
            direction = "decreased" if score_delta < 0 else "increased"
            answer = f"VERIFIED FACT:\\nThe risk score {direction} by {abs(score_delta)} points (from {previous_score} to {current_score})."'''

repl = '''    elif matched_intent == "why_risk":
        if not scan.risk_score:
            answer = "VERIFIED FACT:\\nRisk score is currently unavailable for this commit."
        else:
            score_delta = scan.risk_score.score_delta or 0
            current_score = scan.risk_score.score
            previous_score = current_score - score_delta
            
            if score_delta == 0:
                answer = f"VERIFIED FACT:\\nThe risk score did not change (remained at {current_score})."
            else:
                direction = "decreased" if score_delta < 0 else "increased"
                answer = f"VERIFIED FACT:\\nThe risk score {direction} by {abs(score_delta)} points (from {previous_score} to {current_score})."'''

if target in code:
    code = code.replace(target, repl)
    with open('backend/app/api/routes/repositories.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print('SUCCESS')
else:
    print('NOT FOUND')
