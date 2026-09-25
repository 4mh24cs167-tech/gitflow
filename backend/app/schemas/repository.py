from pydantic import BaseModel

class RepositoryBase(BaseModel):
    name: str
    url: str

class RepositoryCreate(RepositoryBase):
    pass

class RepositoryResponse(RepositoryBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True
