"""
models/product.py
=================
جدول المنتجات — يُخزّن كل بيانات المنتج بما فيها الباركود والمعلومات الصحية.
نُقل من الباك اند القديم مع إضافة حقل rfid_tag.
"""
from sqlalchemy import Column, Integer, String, Float, Text
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
