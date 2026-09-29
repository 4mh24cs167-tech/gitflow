with open("backend/app/database/models.py", "r", encoding="utf-8") as f:
    content = f.read()

old_repo = """class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("User", back_populates="repositories")"""

new_repo = """class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    provider = Column(String, default="github")
    github_owner = Column(String, nullable=True)
    default_branch = Column(String, nullable=True)
    is_public = Column(Boolean, default=True)
    github_created_at = Column(DateTime(timezone=True), nullable=True)
    github_updated_at = Column(DateTime(timezone=True), nullable=True)
    monitoring_enabled = Column(Boolean, default=True)

    owner = relationship("User", back_populates="repositories")"""

content = content.replace(old_repo, new_repo)

# Ensure DateTime is imported
if "DateTime" not in content:
    content = content.replace("from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint", "from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, DateTime")

with open("backend/app/database/models.py", "w", encoding="utf-8") as f:
    f.write(content)
