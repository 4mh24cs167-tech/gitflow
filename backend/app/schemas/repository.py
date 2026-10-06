from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class RepositoryBase(BaseModel):
    name: str
    url: str

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryResponse(RepositoryBase):
    id: int
    owner_id: int
    provider: Optional[str] = "github"
    github_owner: Optional[str] = None
    default_branch: Optional[str] = None
    is_public: Optional[bool] = True
    github_created_at: Optional[datetime] = None
    github_updated_at: Optional[datetime] = None
    monitoring_status: Optional[str] = "NOT_CONFIGURED"
    last_polled_at: Optional[datetime] = None
    last_successful_poll_at: Optional[datetime] = None
    last_processed_sha: Optional[str] = None
    last_seen_sha: Optional[str] = None
    last_poll_error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
