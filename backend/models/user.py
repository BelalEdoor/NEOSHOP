"""
models/user.py
==============
جدول المستخدمين — يدعم العملاء وأصحاب المتاجر وموظفي الأمن.
نُقل من الباك اند القديم مع إضافة حقول age, gender للملف الصحي.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    OWNER    = "owner"
    SECURITY = "security"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)

    # ─── Customer Health Profile ───────────────────────────────────────────
    age       = Column(Integer, nullable=True)
    gender    = Column(String(10), nullable=True)
    allergies = Column(Text, nullable=True)  # JSON: ["milk","nuts"]

    # ─── Owner / Security Extra Info ──────────────────────────────────────
    business_name   = Column(String(200), nullable=True)
    license_number  = Column(String(100), nullable=True)
    badge_number    = Column(String(50),  nullable=True)
    shift_schedule  = Column(String(200), nullable=True)
    clearance_level = Column(Integer,     default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    sessions = relationship("ShoppingSession", back_populates="user",
                            cascade="all, delete-orphan")
