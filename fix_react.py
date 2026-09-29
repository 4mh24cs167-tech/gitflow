with open('frontend/src/pages/RiskPassport.tsx', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace('import React, { useState', 'import { useState')
with open('frontend/src/pages/RiskPassport.tsx', 'w', encoding='utf-8') as f:
    f.write(code)
