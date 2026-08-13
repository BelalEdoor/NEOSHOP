"""
migrate_theft_enum.py
=====================
ترحيل صغير يُشغَّل **مرة واحدة** بعد تحديث نظام كشف السرقة.

لماذا هو ضروري؟
    عمود `theft_logs.alert_type` معرَّف كـ ENUM في MySQL. أُضيفت ثلاث قيم
    جديدة للنظام:

        PLEASE_SCAN_PRODUCT   — تحذير الـ ٨ ثوانٍ على نقطة البيع
        PRODUCT_NOT_SCANNED   — انتهت المهلة دون مسح ➜ تصعيد
        BRAKE_RELEASED        — تحرير الفرامل بزر "تفعيل السلة"

    و `Base.metadata.create_all()` تُنشئ الجداول الناقصة فقط ولا تعدّل
    جدولاً موجوداً. بدون هذا الترحيل سيرمي MySQL خطأ
    `Data truncated for column 'alert_type'` أول مرة يحاول النظام تسجيل
    تنبيه من النوع الجديد — أي أول مرة يشتغل الكشف فعلياً.

التشغيل (من داخل مجلد backend):
    python migrate_theft_enum.py

آمن للتكرار: تشغيله أكثر من مرة لا يسبب أي ضرر.
قواعد SQLite لا تحتاجه إطلاقاً (تخزّن الـ ENUM كنص) — السكربت يتخطّاها.
"""
import sys

from sqlalchemy import text

from core.config import settings
from core.database import engine
from models.theft import TheftAlertType

TABLE = "theft_logs"
COLUMN = "alert_type"


def build_enum_definition() -> str:
    values = ", ".join(f"'{t.value}'" for t in TheftAlertType)
    return f"ENUM({values}) NOT NULL"


def main() -> int:
    url = settings.DATABASE_URL

    if url.startswith("sqlite"):
        print("✓ قاعدة SQLite — لا حاجة لأي ترحيل (تُخزَّن الـ ENUM كنص).")
        return 0

    if "mysql" not in url:
        print(f"⚠️ نوع قاعدة بيانات غير متوقَّع ({url.split('://')[0]}).")
        print("   راجع تعريف عمود alert_type يدوياً وأضف القيم الجديدة.")
        return 1

    definition = build_enum_definition()
    statement = f"ALTER TABLE {TABLE} MODIFY COLUMN {COLUMN} {definition}"

    print("سيتم تنفيذ:")
    print(f"  {statement}\n")

    try:
        with engine.begin() as conn:
            exists = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = :t"
            ), {"t": TABLE}).scalar()

            if not exists:
                print(f"جدول {TABLE} غير موجود بعد — سيُنشئه التطبيق تلقائياً "
                      f"بالقيم الصحيحة عند أول تشغيل. لا حاجة لهذا الترحيل.")
                return 0

            conn.execute(text(statement))

        print("✅ تم التحديث بنجاح. القيم المدعومة الآن:")
        for t in TheftAlertType:
            print(f"   · {t.value}")
        return 0

    except Exception as e:
        print(f"❌ فشل الترحيل: {e}")
        print("\nيمكنك تنفيذ الأمر يدوياً من MySQL:")
        print(f"  {statement};")
        return 1


if __name__ == "__main__":
    sys.exit(main())
