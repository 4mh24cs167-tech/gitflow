import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Software Risk Passport"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://passport_user:passport_password@localhost:5432/risk_passport"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "super-secret-webhook-key")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    GITHUB_OAUTH_STATE_TTL_SECONDS: int = 600
    SCAN_TIMEOUT_SECONDS: int = 120
    GITHUB_TOKEN_ENCRYPTION_KEY: str = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", "uE2N2wF5bCq-H6sVlqQhM5mZl3fA7xP4V2bJ0rA1h10=")

    class Config:
        env_file = ".env"

settings = Settings()
