"""
models/recommendation_engine.py
================================
الجداول الجديدة الخاصة بمحرّك التوصيات الصحي:
  - Allergen: قائمة موحدة بالمواد المسبّبة للحساسية (نفس الأسماء
    المستخدمة في الواجهة الأمامية، مثل "milk", "peanuts").
  - CustomerAllergy: حساسيات كل مستخدم (مرتبطة بـ users.id الحقيقي).
  - ProductAllergen: مكوّنات الحساسية في كل منتج (مرتبطة بـ products.id).
  - HealthCondition: الحالات الصحية (سكري، ضغط...) المرتبطة بعنصر غذائي
    رقمي يمكن قياسه (سكر، صوديوم، سعرات).
  - CustomerHealthCondition: حالات كل مستخدم، بدرجة شدّة.

ملاحظة مهمة: هذا الملف إضافي بالكامل، ولا يُعدّل على users.py أو
product.py. الـ allergies الموجودة حالياً كـ JSON نصي في User.allergies
تبقى كما هي للتوافق مع الواجهة الأمامية — هذه الجداول تُستخدم داخلياً
فقط من قبل routers/analysis.py لمطابقة أدق وأسرع.
"""
from sqlalchemy import (
    Column, Integer, String, DECIMAL, Boolean, Enum, ForeignKey, DateTime
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base
import enum


class Allergen(Base):
    """
    قائمة موحدة بالحساسيات. الأسماء بصيغة lowercase تطابق تماماً
    القائمة المستخدمة في frontend/src/pages/ProfilePage.jsx
    (COMMON_ALLERGIES) لضمان عدم الحاجة لأي تعديل في الواجهة.
    """
    __tablename__ = "allergens"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "milk"
    name_ar     = Column(String(50), nullable=True)  # للعرض على شاشة العربة بالعربي


class CustomerAllergy(Base):
    """حساسية واحدة لمستخدم واحد."""
    __tablename__ = "customer_allergies"

    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    allergen_id = Column(Integer, ForeignKey("allergens.id", ondelete="CASCADE"), primary_key=True)

    allergen = relationship("Allergen")


class ProductAllergen(Base):
    """حساسية واحدة موجودة في منتج واحد."""
    __tablename__ = "product_allergens"

    product_id  = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    allergen_id = Column(Integer, ForeignKey("allergens.id", ondelete="CASCADE"), primary_key=True)

    allergen = relationship("Allergen")


class HealthCondition(Base):
    """
    حالة صحية مرتبطة بعنصر غذائي رقمي على Product
    (مثل sugar_g أو sodium_mg أو calories).
    """
    __tablename__ = "health_conditions"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(100), unique=True, nullable=False)   # e.g. "Diabetes"
    name_ar           = Column(String(100), nullable=True)                  # e.g. "السكري"
    related_nutrient  = Column(String(50), nullable=True)                   # "sugar" | "sodium" | "calories"
    warning_threshold = Column(DECIMAL(6, 2), nullable=True)                # القيمة التي يبدأ بعدها التحذير


class SeverityEnum(str, enum.Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class CustomerHealthCondition(Base):
    """حالة صحية واحدة لمستخدم واحد، مع درجة شدّة."""
    __tablename__ = "customer_health_conditions"

    user_id      = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    condition_id = Column(Integer, ForeignKey("health_conditions.id", ondelete="CASCADE"), primary_key=True)
    severity     = Column(Enum(SeverityEnum), nullable=False, default=SeverityEnum.moderate)

    condition = relationship("HealthCondition")


class RecommendationTypeEnum(str, enum.Enum):
    block = "block"
    warning = "warning"
    suitable = "suitable"


class CustomerActionEnum(str, enum.Enum):
    accepted_alt = "accepted_alt"
    ignored = "ignored"
    added_anyway = "added_anyway"


class RecommendationLog(Base):
    """
    سجل كل توصية عرضها النظام على العميل — مفيد لقياس أداء المحرّك
    في فصل التقييم بالتقرير (نسبة قبول الاقتراحات البديلة، إلخ).
    """
    __tablename__ = "recommendation_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    session_id          = Column(Integer, ForeignKey("shopping_sessions.id", ondelete="CASCADE"), nullable=False)
    original_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    recommendation_type = Column(Enum(RecommendationTypeEnum), nullable=False)
    suggested_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    reason_code         = Column(String(150), nullable=True)
    customer_action      = Column(Enum(CustomerActionEnum), nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
