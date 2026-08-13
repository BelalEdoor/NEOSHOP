"""
models/theft.py
===============
سجل أحداث السرقة المكتشفة من نظام Computer Vision (YOLOv8).
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base
import enum


class TheftAlertType(str, enum.Enum):
    UNSCANNED_ITEM     = "UNSCANNED_ITEM"      # منتج لم يُسحب بالسكانر
    SUSPICIOUS_MOVEMENT = "SUSPICIOUS_MOVEMENT" # حركة مشبوهة
    ITEM_CONCEALED     = "ITEM_CONCEALED"       # إخفاء منتج
    MULTIPLE_ITEMS     = "MULTIPLE_ITEMS"       # أخذ عدة منتجات دفعة واحدة
    BRAKE_ACTIVATED    = "BRAKE_ACTIVATED"      # تفعيل الفرامل
    BRAKE_RELEASED     = "BRAKE_RELEASED"       # تحرير الفرامل (زر "تفعيل السلة" بالداشبورد)
    # ─── من محرّك cv/theft_logic.py (اكتشاف اليد + المنطقتين) ─────────────
    PROLONGED_HOLDING  = "PROLONGED_HOLDING"    # منتج بيد العميل بمنطقة المسح دون مسح لفترة طويلة
    UNSCANNED_IN_CART  = "UNSCANNED_IN_CART"    # منتج استقرّ داخل السلة دون أي مسح مسجَّل
    # ─── سير العمل الحالي (Zone A / Zone B + مراقبة الفاتورة) ─────────────
    PLEASE_SCAN_PRODUCT = "PLEASE_SCAN_PRODUCT"  # تحذير ٨ ثوانٍ على نقطة البيع: أعد مسح المنتج
    PRODUCT_NOT_SCANNED = "PRODUCT_NOT_SCANNED"  # انتهت المهلة دون مسح ➜ تصعيد للفرامل
    # ─── إرجاع منتج (B→A) وكشف تغطية الكاميرا ──────────────────────────────
    ITEM_RETURNED_NOT_REMOVED = "ITEM_RETURNED_NOT_REMOVED"  # أُخرج منتج من السلة ولم يُحذف من الفاتورة — تحذير فقط، بدون فرامل
    CAMERA_OBSTRUCTED = "CAMERA_OBSTRUCTED"                  # تغطية متعمّدة للعدسة (٣ ثوانٍ) ➜ فرامل فورية


class TheftLog(Base):
    __tablename__ = "theft_logs"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="SET NULL"), nullable=True)

    alert_type       = Column(Enum(TheftAlertType), nullable=False)
    description      = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)   # نسبة ثقة YOLO

    # ─── Response ─────────────────────────────────────────────────────────
    brake_activated    = Column(Boolean, default=False)
    customer_notified  = Column(Boolean, default=False)
    security_notified  = Column(Boolean, default=False)
    resolved           = Column(Boolean, default=False)
    resolved_by_user_id = Column(Integer, nullable=True)

    # ─── Timestamps ───────────────────────────────────────────────────────
    detected_at  = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at  = Column(DateTime(timezone=True), nullable=True)

    # ─── Relationships ─────────────────────────────────────────────────────
    session = relationship("ShoppingSession", back_populates="theft_logs")