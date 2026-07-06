"""
models/product.py
=================
جدول المنتجات — يُخزّن كل بيانات المنتج بما فيها الباركود والمعلومات الصحية.
نُقل من الباك اند القديم مع إضافة حقل rfid_tag.
"""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from core.database import Base


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False, index=True)
    name_ar     = Column(String(255), nullable=True)
    price       = Column(Float, nullable=False)
    barcode     = Column(String(100), unique=True, index=True, nullable=True)
    quantity    = Column(Integer, default=100)
    category    = Column(String(100), nullable=True)
    brand       = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=True)  # Comma-separated
    allergens   = Column(Text, nullable=True)  # Comma-separated
    image_url   = Column(String(500), nullable=True)

    # ─── Store Location ────────────────────────────────────────────────────
    location_x = Column(Integer, default=0)
    location_y = Column(Integer, default=0)
    section    = Column(String(100), nullable=True)

    # ─── Nutrition (added for the Recommendation Engine's warning tier) ───
    # القيم الرقمية لكل حصة (per serving) — تُستخدم لمقارنة الحالات الصحية
    # مثل السكري وضغط الدم. Optional, may be NULL إذا لم تُدخل القيمة بعد.
    sugar_g    = Column(Float, nullable=True)  # جرام سكر
    sodium_mg  = Column(Float, nullable=True)  # ملغرام صوديوم
    calories   = Column(Float, nullable=True)  # سعرات حرارية

    # ─── Offers / Discounts (added) ────────────────────────────────────────
    # Real offer data set by the store owner via the admin panel, instead
    # of the previous hardcoded mock list in frontend/src/data/offersData.js.
    # old_price is only meaningful when is_on_offer is True; price stays the
    # actual current/charged price (so cart/checkout logic is unaffected).
    is_on_offer    = Column(Boolean, default=False, nullable=False)
    old_price      = Column(Float, nullable=True)   # original price before discount
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)  # null = no expiry

