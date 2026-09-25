from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    github_access_token = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")

class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (UniqueConstraint('repository_id', 'hash', name='uq_commit_repo_hash'),)

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String, index=True, nullable=False)
    message = Column(String)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)

    repository = relationship("Repository", back_populates="commits")
    scans = relationship("Scan", back_populates="commit", cascade="all, delete-orphan")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String, default="QUEUED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    commit = relationship("Commit", back_populates="scans")
    error_message = Column(String, nullable=True)
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    risk_score = relationship("RiskScore", back_populates="scan", uselist=False, cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    fingerprint = Column(String, index=True, nullable=False)
    status = Column(String, default="NEW") # NEW, UNCHANGED, RESOLVED
    type = Column(String)  # secret, dependency, license, large_file
    description = Column(Text)
    file_path = Column(String)
    line_number = Column(Integer, nullable=True)
    severity = Column(String, default="Medium")

    scan = relationship("Scan", back_populates="findings")

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    score = Column(Integer, default=100)
    score_delta = Column(Integer, nullable=True)
    details = Column(Text)

    scan = relationship("Scan", back_populates="risk_score")
