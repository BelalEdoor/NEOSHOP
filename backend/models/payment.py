"""
models/payment.py
=================
جدولان:
  1. Payment — سجل الدفع الرئيسي المرتبط بالفاتورة.
  2. PaymentTransaction — كل عملية إدخال عملة/ورقة نقدية بشكل منفصل.
     يُتيح Real-Time Payment Tracking.
"""
from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    PENDING    = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_REFILL = "AWAITING_REFILL"  # نفدت أنابيب العملات — الدفعة متوقفة مؤقتاً
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    REFUNDED   = "REFUNDED"


class PaymentMethod(str, enum.Enum):
    CASH  = "CASH"
    COIN  = "COIN"
    MIXED = "MIXED"  # نقود ورقية + معدنية معاً


class Payment(Base):
    """سجل الدفع الكامل."""
    __tablename__ = "payments"

    id         = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)

    # ─── Financial ────────────────────────────────────────────────────────
    total_due      = Column(Float, nullable=False)
    amount_inserted = Column(Float, default=0.0)
    change_returned = Column(Float, default=0.0)
    # NEW — المبلغ (NIS) اللي لسا الجهاز لازم يرجعه للعميل، معبّى فقط وقت
    # AWAITING_REFILL. صفر يعني ما في شي معلّق.
    pending_change = Column(Float, default=0.0)
    # NEW — سجل تاريخي لحدث نفاد الأنابيب (يبقى محفوظ حتى بعد ما تُحل
    # المشكلة، عشان تُبنى عليه صفحة "الإشعارات / السجل" بلوحة الأدمن).
    # refill_amount يحفظ آخر مبلغ طُلب تعبئته (ما بيتصفر بعد الحل، بعكس
    # pending_change اللي بيرجع صفر فور اكتمال الدفعة).
    refill_requested_at = Column(DateTime(timezone=True), nullable=True)
    refill_resolved_at  = Column(DateTime(timezone=True), nullable=True)
    refill_amount       = Column(Float, nullable=True)
    method         = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)

    # ─── Status ───────────────────────────────────────────────────────────
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    # ─── ESP32 Info ───────────────────────────────────────────────────────
    cart_rfid       = Column(String(100), nullable=True)
    esp32_device_id = Column(String(50),  nullable=True)

    # ─── Timestamps ───────────────────────────────────────────────────────
    started_at   = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # ─── Relationships ─────────────────────────────────────────────────────
    invoice      = relationship("Invoice", back_populates="payments")
    transactions = relationship("PaymentTransaction", back_populates="payment",
                                cascade="all, delete-orphan")


class TransactionType(str, enum.Enum):
    COIN = "COIN"  # عملة معدنية
    BILL = "BILL"  # ورقة نقدية


class PaymentTransaction(Base):
    """
    كل إدخال عملة أو ورقة نقدية بشكل منفصل.
    يُرسل ESP32 هذه البيانات عبر MQTT في real-time.
    """
    __tablename__ = "payment_transactions"

    id         = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)

    transaction_type = Column(Enum(TransactionType), nullable=False)
    denomination     = Column(Float,  nullable=False)  # قيمة العملة/الورقة
    count            = Column(Integer, default=1)
    total_value      = Column(Float,  nullable=False)

    inserted_at = Column(DateTime(timezone=True), server_default=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    payment = relationship("Payment", back_populates="transactions")