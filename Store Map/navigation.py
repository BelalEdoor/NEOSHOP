"""
models/navigation.py
====================
نظام تحديد الموقع داخل المتجر (النسخة المبسّطة — علامة واحدة لكل قسم):

  1. Section        — القسم (رف/مدخل/مخرج/نقطة دفع) مع إحداثيات النقطة على الخريطة.
  2. Shelf          — الرف الفيزيائي المرتبط بقسم (للتوسع المستقبلي، اختياري).
  3. CartLiveStatus — آخر موقع معروف لكل عربة (النقطة الحمراء على الخريطة).
  4. MarkerReadLog  — سجل كل قراءات العلامات (للتحليل والتصحيح).

نظام الإحداثيات: الأصل (0,0) في الزاوية السفلية اليسرى للمتجر،
X نحو اليمين، Y نحو عمق المتجر، والوحدة متر.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


class Section(Base):
    """قسم في المتجر — نقطة واحدة على الخريطة + علامة ArUco واحدة (إن وجدت)."""
    __tablename__ = "sections"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(100), nullable=False)             # e.g. 'القسم 1'
    name_en   = Column(String(100), nullable=True)              # e.g. 'Section 1'
    kind      = Column(String(20), nullable=False, default="shelf")  # shelf | entrance | exit | payment
    marker_id = Column(Integer, unique=True, nullable=True, index=True)  # ArUco ID (نقطة الدفع بدون علامة)
    map_x     = Column(Float, nullable=False)                   # متر من الجدار الأيسر
    map_y     = Column(Float, nullable=False)                   # متر من الجدار الأمامي

    # ─── Relationships ─────────────────────────────────────────────────────
    shelves = relationship("Shelf", back_populates="section")


class Shelf(Base):
    """رف فيزيائي داخل قسم (اختياري — للتوسع عندما يصبح للقسم أكثر من رف)."""
    __tablename__ = "shelves"

    id           = Column(Integer, primary_key=True, index=True)
    section_id   = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    shelf_label  = Column(String(50), nullable=False)           # e.g. 'Shelf2a'
    display_name = Column(String(100), nullable=True)

    # ─── Relationships ─────────────────────────────────────────────────────
    section = relationship("Section", back_populates="shelves")


class CartLiveStatus(Base):
    """آخر موقع معروف للعربة — صف واحد لكل عربة (upsert عند كل قراءة)."""
    __tablename__ = "cart_live_status"

    cart_id            = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    current_section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    pos_x              = Column(Float, nullable=False, default=0.0)
    pos_y              = Column(Float, nullable=False, default=0.0)
    last_marker_id     = Column(Integer, nullable=True)
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    cart    = relationship("Cart")
    section = relationship("Section")


class MarkerReadLog(Base):
    """سجل قراءات العلامات — لأغراض التحليل والتصحيح."""
    __tablename__ = "marker_read_logs"

    id          = Column(Integer, primary_key=True, index=True)
    cart_id     = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    marker_id   = Column(Integer, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    # ─── Relationships ─────────────────────────────────────────────────────
    cart = relationship("Cart")
