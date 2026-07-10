"""
models/map.py
=============
جداول نظام خريطة المتجر:

  - Section        : أقسام المتجر مع إحداثيات الخريطة
  - Shelf          : الرفوف داخل كل قسم
  - CartLiveStatus : الموقع + الاتجاه الحالي للعربة في الوقت الفعلي
  - MarkerReadLog  : سجل قراءات ArUco لتتبع مسار العربة

التحديثات:
  CartLiveStatus الآن يخزّن:
    - first_marker_id   : أول علامة قُرئت في الممر الحالي
    - first_marker_time : وقت قراءتها
    - direction         : 'forward' أو 'backward' بعد قراءة العلامة الثانية
    - aisle_id          : رقم الممر الحالي (1 أو 2)
    - in_aisle          : هل العربة داخل ممر الآن؟
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class Section(Base):
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(100), nullable=False)
    marker_id  = Column(Integer, nullable=True, unique=True)
    map_x      = Column(Float, nullable=True)
    map_y      = Column(Float, nullable=True)

    shelves = relationship("Shelf", back_populates="section", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("marker_id", name="uq_section_marker"),
    )


class Shelf(Base):
    __tablename__ = "shelves"

    shelf_id     = Column(Integer, primary_key=True, autoincrement=True)
    section_id   = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False)
    shelf_label  = Column(String(20), nullable=False)
    display_name = Column(String(150), nullable=True)

    section = relationship("Section", back_populates="shelves")


class CartLiveStatus(Base):
    __tablename__ = "cart_live_status"

    cart_id            = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    current_section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="SET NULL"), nullable=True)
    pos_x              = Column(Float, nullable=True)
    pos_y              = Column(Float, nullable=True)
    last_marker_id     = Column(Integer, nullable=True)
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── حقول الاتجاه ─────────────────────────────────────────────────────────
    # أول علامة قُرئت في الممر الحالي (قبل اكتمال الحركة)
    first_marker_id   = Column(Integer, nullable=True)
    first_marker_time = Column(DateTime(timezone=True), nullable=True)

    # 'forward'  = قرأ العلامة الأصغر ثم الأكبر (0→1 أو 2→3) → سهم يمين
    # 'backward' = قرأ العلامة الأكبر ثم الأصغر (1→0 أو 3→2) → سهم يسار
    # None       = لم تكتمل الحركة بعد (علامة واحدة فقط)
    direction = Column(String(10), nullable=True)

    # رقم الممر: 1 (بين SEC1 وSEC2) أو 2 (بين SEC2 وSEC3)
    aisle_id  = Column(Integer, nullable=True)

    # True = العربة داخل ممر حالياً (قرأ علامة واحدة ولم يخرج بعد)
    in_aisle  = Column(Boolean, default=False, nullable=False)

    section = relationship("Section")


class MarkerReadLog(Base):
    __tablename__ = "marker_read_log"

    log_id      = Column(Integer, primary_key=True, autoincrement=True)
    cart_id     = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    marker_id   = Column(Integer, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = ({},)
