"""
models/__init__.py
==================
تسجيل جميع نماذج قاعدة البيانات.
استيراد هذا الملف يضمن أن SQLAlchemy يعرف كل الجداول قبل إنشائها.
"""
from models.user import User
from models.product import Product
from models.cart import Cart, CartItem
from models.session import ShoppingSession
from models.invoice import Invoice
from models.payment import Payment, PaymentTransaction
from models.theft import TheftLog

# ─── Recommendation Engine (new) ────────────────────────────────────────────
from models.recommendation_engine import (
    Allergen, CustomerAllergy, ProductAllergen,
    HealthCondition, CustomerHealthCondition,
    RecommendationLog,
)

__all__ = [
    "User", "Product",
    "Cart", "CartItem",
    "ShoppingSession",
    "Invoice",
    "Payment", "PaymentTransaction",
    "TheftLog",
    "Allergen", "CustomerAllergy", "ProductAllergen",
    "HealthCondition", "CustomerHealthCondition",
    "RecommendationLog",
]
