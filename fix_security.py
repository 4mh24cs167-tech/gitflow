with open("backend/app/auth/security.py", "r", encoding="utf-8") as f:
    content = f.read()

import re
content = content.replace("from passlib.context import CryptContext", "import bcrypt")
content = re.sub(r"pwd_context = CryptContext\(schemes=\[\"bcrypt\"\], deprecated=\"auto\"\)\n", "", content)

content = re.sub(r"def verify_password\(plain_password: str, hashed_password: str\) -> bool:\n\s+return pwd_context\.verify\(plain_password, hashed_password\)",
"""def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False""", content)

content = re.sub(r"def get_password_hash\(password: str\) -> str:\n\s+return pwd_context\.hash\(password\)",
"""def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')""", content)

with open("backend/app/auth/security.py", "w", encoding="utf-8") as f:
    f.write(content)
