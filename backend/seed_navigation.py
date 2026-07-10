"""
seed_navigation.py
==================
تعبئة جدول sections بإحداثيات خريطة المتجر الحقيقية.

الإحداثيات مبنية على نظام المتجر في مخطط ERD:
  - الأصل (0,0) في الزاوية السفلية اليسرى
  - محور X: يمين (0 إلى 12 متراً)
  - محور Y: أعلى (0 إلى 8 أمتار)
  - كل قسم له marker_id يطابق رقم العلامة ArUco المطبوعة

التشغيل (مرة واحدة بعد تشغيل الباك اند):
    python seed_navigation.py

آمن لإعادة التشغيل — يتحقق قبل الإضافة.
"""
import sys
sys.path.insert(0, '.')

from core.database import SessionLocal
import models  # noqa: F401 — registers all tables
from models.map import Section, Shelf

SECTIONS = [
    # (name, marker_id, map_x, map_y)
    # الأقسام الرئيسية — الرفوف على طول المتجر
    # marker_id يطابق رقم ArUco المطبوع واللاصق عند مدخل كل قسم
    {"name": "Dairy",      "name_ar": "منتجات الألبان",  "marker_id": 1, "map_x": 2.0, "map_y": 4.0},
    {"name": "Bakery",     "name_ar": "المخبوزات",        "marker_id": 2, "map_x": 4.0, "map_y": 4.0},
    {"name": "Snacks",     "name_ar": "الوجبات الخفيفة", "marker_id": 3, "map_x": 6.0, "map_y": 4.0},
    {"name": "Beverages",  "name_ar": "المشروبات",        "marker_id": 4, "map_x": 8.0, "map_y": 4.0},
    {"name": "Produce",    "name_ar": "الخضار والفواكه",  "marker_id": 5, "map_x": 2.0, "map_y": 6.5},
    {"name": "Meat",       "name_ar": "اللحوم والدواجن", "marker_id": 6, "map_x": 4.0, "map_y": 6.5},
    {"name": "Pantry",     "name_ar": "المواد الجافة",    "marker_id": 7, "map_x": 6.0, "map_y": 6.5},
    {"name": "Frozen",     "name_ar": "المجمدات",         "marker_id": 8, "map_x": 8.0, "map_y": 6.5},
    # نقاط ثابتة: المدخل / المخرج / نقطة الدفع
    {"name": "Entrance",   "name_ar": "المدخل",           "marker_id": 9,  "map_x": 1.0, "map_y": 0.5},
    {"name": "Exit",       "name_ar": "المخرج",           "marker_id": 10, "map_x": 11.0, "map_y": 0.5},
    {"name": "Payment",    "name_ar": "نقطة الدفع",       "marker_id": 11, "map_x": 6.0,  "map_y": 0.5},
]

SHELVES = [
    # (section_name, shelf_label, display_name)
    # ربط الرفوف بأكوادها القديمة في المنتجات (A1, B1, C1...) لضمان التوافق مع
    # المنتجات المحفوظة في قاعدة البيانات بالكود القديم
    ("Dairy",     "A1", "Dairy Shelf A"),
    ("Dairy",     "A2", "Dairy Shelf B"),
    ("Bakery",    "B1", "Bakery Shelf A"),
    ("Bakery",    "B2", "Bakery Shelf B"),
    ("Snacks",    "C1", "Snacks Shelf A"),
    ("Snacks",    "C2", "Snacks Shelf B"),
    ("Beverages", "D1", "Beverages Shelf A"),
    ("Beverages", "D2", "Beverages Shelf B"),
    ("Produce",   "E1", "Produce Area"),
    ("Meat",      "F1", "Meat & Deli Counter"),
]


def seed():
    db = SessionLocal()
    try:
        added_sections = 0
        section_map = {}  # name -> Section object

        for item in SECTIONS:
            existing = db.query(Section).filter(Section.marker_id == item["marker_id"]).first()
            if not existing:
                s = Section(
                    name=item["name"],
                    marker_id=item["marker_id"],
                    map_x=item["map_x"],
                    map_y=item["map_y"],
                )
                db.add(s)
                db.flush()
                section_map[item["name"]] = s
                added_sections += 1
            else:
                section_map[item["name"]] = existing

        added_shelves = 0
        for sec_name, label, display in SHELVES:
            section = section_map.get(sec_name)
            if not section:
                continue
            existing_shelf = db.query(Shelf).filter(
                Shelf.section_id == section.section_id,
                Shelf.shelf_label == label,
            ).first()
            if not existing_shelf:
                db.add(Shelf(
                    section_id=section.section_id,
                    shelf_label=label,
                    display_name=display,
                ))
                added_shelves += 1

        db.commit()
        print(f"✅ Navigation seed complete:")
        print(f"   {added_sections} section(s) added")
        print(f"   {added_shelves} shelf/shelves added")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
