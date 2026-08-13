"""
cv/theft_detection.py
======================
نقطة الدخول القديمة (يستوردها main.py و routers/session.py:
`from cv.theft_detection import theft_service`) — أُبقيت بنفس الاسم
للتوافق، لكن التنفيذ الفعلي موجود في الوحدات المتخصصة:

    cv/config.py          — كل الثوابت القابلة للتعديل (المنطقتان، العتبات، الفئات)
    cv/detector.py        — غلاف YOLOv8 (نموذج مدرَّب best.pt) + MediaPipe Hands
    cv/zones.py           — هندسة المنطقتين: Zone A (مسح) / Zone B (السلة)
    cv/tracker.py         — تتبّع الكائنات بين الإطارات (IoU) وأحداث دخول السلة
    cv/receipt_monitor.py — مراقبة الفاتورة: هل أُضيف سطر جديد بعد نزول المنتج؟
    cv/theft_logic.py     — طبقة القرار: PLEASE_SCAN_PRODUCT / PRODUCT_NOT_SCANNED
    cv/alert_handler.py   — الجسر مع باقي النظام (DB + WebSocket + الفرامل)

هذا الملف يُصدِّر فقط الأسماء التي يعتمد عليها بقية الباك اند
(`theft_service`, `TheftDetectionService`) حتى لا تحتاج main.py أو أي
مستورد آخر لأي تعديل.
"""
from cv.theft_logic import theft_service, TheftDetectionService  # noqa: F401
