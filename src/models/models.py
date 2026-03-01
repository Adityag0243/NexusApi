import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.models.base import Base

class Organisation(Base):
    __tablename__ = "organisations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    name = Column(String, nullable=False) 
    slug = Column(String, unique=True, index=True, nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow) 

    users = relationship("User", back_populates="organisation")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    email = Column(String, unique=True, index=True, nullable=False) 
    name = Column(String) 
    google_id = Column(String, unique=True) 
    organisation_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False) 
    role = Column(String, default="member")  # "admin" or "member" 
    created_at = Column(DateTime, default=datetime.utcnow) 

    organisation = relationship("Organisation", back_populates="users")

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    organisation_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id"), index=True, nullable=False) 
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False) 
    amount = Column(Integer, nullable=False)  # Positive for grants, negative for spend 
    reason = Column(Text) 
    idempotency_key = Column(String, unique=True, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow) 

    __table_args__ = (
        Index("ix_org_credits_created", "organisation_id", "created_at"),
    )