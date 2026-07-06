"""
seed_recommendation_engine.py
==============================
يُدرج قائمة ابتدائية من الحساسيات والحالات الصحية في الجداول الجديدة.
الأسماء مطابقة تماماً لـ COMMON_ALLERGIES في
frontend/src/pages/ProfilePage.jsx — هذا مقصود ومهم، لأن المطابقة
بين User.allergies (JSON نصي) والجداول المنظَّمة تعتمد على تطابق الاسم.

شغّله مرة واحدة بعد أول تشغيل للباك اند (بعد create_all):
    python seed_recommendation_engine.py

آمن لإعادة التشغيل: يتحقق من وجود الاسم قبل الإضافة.
"""
from core.database import SessionLocal
import models  # noqa: F401
from models.recommendation_engine import Allergen, HealthCondition

# مطابقة تماماً لـ ProfilePage.jsx -> COMMON_ALLERGIES، بالإضافة لإضافتين
# مدعومتين ببيانات انتشار إقليمية (راجع seed_data.py القديم للمصادر).
ALLERGENS = [
    {"name": "milk",      "ar": "الحليب"},
    {"name": "nuts",      "ar": "المكسرات"},
    {"name": "peanuts",   "ar": "الفول السوداني"},
    {"name": "gluten",    "ar": "الغلوتين"},
    {"name": "eggs",      "ar": "البيض"},
    {"name": "soy",       "ar": "فول الصويا"},
    {"name": "fish",      "ar": "الأسماك"},
    {"name": "shellfish", "ar": "المحاريات والقشريات"},
    {"name": "sesame",    "ar": "السمسم"},
    {"name": "sulfites",  "ar": "الكبريتات"},
    # إضافات إقليمية (ليست في COMMON_ALLERGIES الافتراضية، لكنها مدعومة
    # بنفس الجدول — العميل يمكنه إضافتها يدوياً عبر حقل "Add allergy")
    {"name": "fruits",    "ar": "الفواكه"},
    {"name": "spices",    "ar": "التوابل والفلفل الحار"},
]

HEALTH_CONDITIONS = [
    {"name": "Diabetes",      "name_ar": "السكري",        "nutrient": "sugar",    "threshold": 15.00},
    {"name": "Hypertension",  "name_ar": "ضغط الدم",       "nutrient": "sodium",   "threshold": 400.00},
    {"name": "Obesity",       "name_ar": "السمنة",         "nutrient": "calories", "threshold": 300.00},
    # ملاحظة: حساسية الغلوتين (Celiac) تُعالَج عبر جدول Allergen
    # (الاسم "gluten") بدل عتبة رقمية، لأن أي كمية غلوتين تُعتبر خطراً.
]


def seed():
    db = SessionLocal()
    try:
        added_allergens = 0
        for item in ALLERGENS:
            if not db.query(Allergen).filter(Allergen.name == item["name"]).first():
                db.add(Allergen(name=item["name"], name_ar=item["ar"]))
                added_allergens += 1

        added_conditions = 0
        for c in HEALTH_CONDITIONS:
            if not db.query(HealthCondition).filter(HealthCondition.name == c["name"]).first():
                db.add(HealthCondition(
                    name=c["name"], name_ar=c["name_ar"],
                    related_nutrient=c["nutrient"], warning_threshold=c["threshold"],
                ))
                added_conditions += 1

        db.commit()
        print(f"✅ Seed complete: {added_allergens} allergen(s), {added_conditions} health condition(s) added.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
