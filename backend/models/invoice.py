"""
models/invoice.py
=================
الفاتورة — تُنشأ عند ضغط "Finish Shopping".
تُرسَل بياناتها إلى MQTT Broker ثم يستلمها ESP32.
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Text, Enum, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


class InvoiceStatus(str, enum.Enum):
    CREATED    = "CREATED"    # تم إنشاؤها
    SENT       = "SENT"       # أُرسلت إلى MQTT
    PROCESSING = "PROCESSING" # ESP32 يعالجها
    PAID       = "PAID"       # تم الدفع
    CANCELLED  = "CANCELLED"  # مُلغاة


class Invoice(Base):
    __tablename__ = "invoices"

    id           = Column(Integer, primary_key=True, index=True)
    invoice_code = Column(String(50), unique=True, index=True)  # e.g. "INV-20260529-001"
    session_id   = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="SET NULL"), nullable=True)
    cart_rfid    = Column(String(100), index=True, nullable=True)  # للبحث من ESP32

    # ─── Financial ────────────────────────────────────────────────────────
    subtotal     = Column(Float, default=0.0)
    discount     = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    # ─── Status ───────────────────────────────────────────────────────────
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.CREATED)

    # ─── Items Snapshot (JSON) ────────────────────────────────────────────
    # نُخزّن snapshot من العناصر لأن الفاتورة يجب أن تبقى ثابتة بعد الإنشاء
    items_json = Column(Text, nullable=True)  # JSON list of items

    # ─── Timestamps ───────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at    = Column(DateTime(timezone=True), nullable=True)

    # ─── Relationships ─────────────────────────────────────────────────────
    session  = relationship("ShoppingSession", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")
