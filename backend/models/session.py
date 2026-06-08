"""
models/session.py
=================
جلسة التسوق — تربط المستخدم بالعربة وتتتبع دورة حياة كاملة من البداية حتى الدفع.

Session Lifecycle:
  1. تُنشأ عند تسجيل دخول العميل وتبدأ بحالة ACTIVE.
  2. عندما يضغط "Finish Shopping" → PENDING_PAYMENT وتُنشأ الفاتورة.
  3. عندما يقرأ ESP32 الـ RFID → PAYMENT_IN_PROGRESS.
  4. بعد اكتمال الدفع → PAID وتُغلق الجلسة.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
from models.cart import CartStatus
import enum


class ShoppingSession(Base):
    __tablename__ = "shopping_sessions"

    id         = Column(Integer, primary_key=True, index=True)

    # ─── Relationships Keys ────────────────────────────────────────────────
    user_id  = Column(Integer, ForeignKey("users.id",  ondelete="SET NULL"), nullable=True)
    cart_id  = Column(Integer, ForeignKey("carts.id",  ondelete="SET NULL"), nullable=True)

    # ─── Session Identity ──────────────────────────────────────────────────
    # cart_rfid: نُخزّن RFID هنا للبحث السريع من ESP32
    cart_rfid  = Column(String(100), index=True, nullable=True)
    status     = Column(Enum(CartStatus), default=CartStatus.ACTIVE, nullable=False)

    # ─── Financial Summary ─────────────────────────────────────────────────
    total_amount = Column(Float, default=0.0)
    discount     = Column(Float, default=0.0)

    # ─── Timestamps ───────────────────────────────────────────────────────
    started_at  = Column(DateTime(timezone=True), server_default=func.now())
    ended_at    = Column(DateTime(timezone=True), nullable=True)
    payment_started_at   = Column(DateTime(timezone=True), nullable=True)
    payment_completed_at = Column(DateTime(timezone=True), nullable=True)

    # ─── Meta ─────────────────────────────────────────────────────────────
    notes = Column(Text, nullable=True)

    # ─── Relationships ─────────────────────────────────────────────────────
    user    = relationship("User",    back_populates="sessions")
    cart    = relationship("Cart",    back_populates="sessions")
    items   = relationship("CartItem",  back_populates="session", cascade="all, delete-orphan")
    invoice = relationship("Invoice",   back_populates="session", uselist=False)
    theft_logs = relationship("TheftLog", back_populates="session")
