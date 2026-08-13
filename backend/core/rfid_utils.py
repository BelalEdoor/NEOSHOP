"""
core/rfid_utils.py
===================
تطبيع (normalize) قيم RFID عبر كل النظام.

المشكلة: نفس البطاقة ممكن توصل بصيغ مختلفة حسب المصدر —
  "D4483AD5"      (Raspberry Pi / قارئ خام)
  "D4:48:3A:D5"   (بعض قارئات RFID اللي بتفصل البايتات بـ ':')
  "d4483ad5"      (حالة أحرف مختلفة)
كل هذه يجب أن تُطابَق كنفس العربة. أي مكان بالكود يقارن أو يخزّن
RFID (Cart.rfid_uid, ShoppingSession.cart_rfid, MQTT payloads,
WebSocket path params) لازم يمرّ عبر normalize_rfid() أولاً.
"""


def normalize_rfid(rfid: str | None) -> str:
    """
    يوحّد صيغة RFID: يشيل الفواصل الشائعة (':' و '-' و المسافات)
    ويحوّل لأحرف كبيرة. القيمة الفارغة أو None ترجع سلسلة فارغة.

    أمثلة:
        "d4:48:3a:d5"      -> "D4483AD5"
        "D4-48-3A-D5"      -> "D4483AD5"
        "  D4483AD5  "     -> "D4483AD5"
        "RFID-DEFAULT-001" -> "RFIDDEFAULT001"
    """
    if not rfid:
        return ""
    return (
        rfid.strip()
        .upper()
        .replace(":", "")
        .replace("-", "")
        .replace(" ", "")
    )
