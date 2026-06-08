"""
models/cart.py
==============
جدولان:
  1. Cart — العربة الفيزيائية مع RFID UID الخاص بها.
     RFID هنا هو Cart Identifier فقط (ليس Session Creator).
  2. CartItem — العناصر داخل جلسة التسوق.

العلاقة:
  Cart (RFID) ←→ ShoppingSession (تربط العربة بجلسة تسوق معيّنة)
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


class CartStatus(str, enum.Enum):
    """
    حالات العربة (Cart State Machine):

    ACTIVE            — العربة نشطة والعميل يتسوق حالياً.
    PENDING_PAYMENT   — انتهى العميل من التسوق وضغط "Finish Shopping"،
                        الفاتورة جاهزة وتنتظر الدفع عند محطة الدفع.
    PAYMENT_IN_PROGRESS — ESP32 قرأ RFID وبدأ عملية الدفع فعلياً.
    PAID              — تم الدفع بنجاح وأُغلقت الجلسة.
    CANCELLED         — ألغى العميل الدفع أو انتهت مهلة الانتظار.
    FAILED            — فشلت عملية الدفع لسبب تقني.
    """
    ACTIVE              = "ACTIVE"
    PENDING_PAYMENT     = "PENDING_PAYMENT"
    PAYMENT_IN_PROGRESS = "PAYMENT_IN_PROGRESS"
    PAID                = "PAID"
    CANCELLED           = "CANCELLED"
    FAILED              = "FAILED"


class Cart(Base):
    """
    العربة الفيزيائية — ثابتة في المتجر.
    كل عربة لها RFID UID مُضمَّن فيها وهو معرّفها الدائم.
    """
    __tablename__ = "carts"

    id          = Column(Integer, primary_key=True, index=True)
    cart_number = Column(String(50), unique=True, nullable=False)  # e.g. "CART-001"
    rfid_uid    = Column(String(100), unique=True, index=True, nullable=False)  # RFID tag UID
    status      = Column(Enum(CartStatus), default=CartStatus.ACTIVE, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    sessions = relationship("ShoppingSession", back_populates="cart")


class CartItem(Base):
    """
    عنصر داخل جلسة تسوق — يرتبط بالجلسة وليس بالعربة مباشرة.
    """
    __tablename__ = "cart_items"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity   = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)  # السعر وقت الإضافة (لحماية من تغيير الأسعار)
    added_at   = Column(DateTime(timezone=True), server_default=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    session = relationship("ShoppingSession", back_populates="items")
