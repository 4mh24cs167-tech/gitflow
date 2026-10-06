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
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GITHUB_OAUTH_STATE_TTL_SECONDS: int = 600
    SCAN_TIMEOUT_SECONDS: int = 120
    CRON_SECRET: str = os.getenv("GITFLOW_CRON_SECRET", "")
    MAX_COMMITS_PER_POLL: int = int(os.getenv("MAX_COMMITS_PER_POLL", "10"))
    MAX_POLLING_RUNTIME_SECONDS: int = int(os.getenv("MAX_POLLING_RUNTIME_SECONDS", "240"))
    MAX_CONCURRENT_SCANS: int = int(os.getenv("MAX_CONCURRENT_SCANS", "2"))
    GITHUB_TOKEN_ENCRYPTION_KEY: str = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY", "uE2N2wF5bCq-H6sVlqQhM5mZl3fA7xP4V2bJ0rA1h10=")

    class Config:
        env_file = ".env"

settings = Settings()

def validate_security_settings(config: Settings) -> None:
    """Reject development secrets and insecure frontend origins in production."""
    is_production = config.ENVIRONMENT.strip().lower() in {"production", "prod"}
    if is_production and not config.FRONTEND_URL.startswith("https://"):
        raise RuntimeError("Production requires FRONTEND_URL to use HTTPS")

    # Keep local development convenient, but never let the known fallback values
    # protect production sessions, webhook requests, repository polling, or tokens.
    if is_production or config.FRONTEND_URL.startswith("https://"):
        unsafe_defaults = {
            "SECRET_KEY": "your-super-secret-key",
            "GITHUB_WEBHOOK_SECRET": "super-secret-webhook-key",
            "GITHUB_TOKEN_ENCRYPTION_KEY": "uE2N2wF5bCq-H6sVlqQhM5mZl3fA7xP4V2bJ0rA1h10=",
            "CRON_SECRET": "",
        }
        missing_secrets = [
            name for name, default_value in unsafe_defaults.items()
            if not getattr(config, name) or getattr(config, name) == default_value
        ]
        if missing_secrets:
            raise RuntimeError(
                "Production requires unique values for: " + ", ".join(missing_secrets)
            )


validate_security_settings(settings)
