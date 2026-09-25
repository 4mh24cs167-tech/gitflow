from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

from cryptography.fernet import Fernet, InvalidToken

_fernet = Fernet(settings.GITHUB_TOKEN_ENCRYPTION_KEY.encode())

def encrypt_token(plain_token: str) -> str:
    if not plain_token:
        return plain_token
    return _fernet.encrypt(plain_token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return encrypted_token
    # check if it looks encrypted (could be plain if old data)
    if not encrypted_token.startswith("gAAAAA"):
        return encrypted_token
    try:
        return _fernet.decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        return ""  # Invalid or corrupted token, requires re-auth
