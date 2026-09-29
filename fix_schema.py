with open("backend/app/schemas/repository.py", "r", encoding="utf-8") as f:
    content = f.read()

new_content = """from pydantic import BaseModel
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
    monitoring_enabled: Optional[bool] = True

    class Config:
        from_attributes = True
"""
with open("backend/app/schemas/repository.py", "w", encoding="utf-8") as f:
    f.write(new_content)
