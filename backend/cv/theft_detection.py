"""
cv/theft_detection.py
======================
نقطة الدخول القديمة (يستوردها main.py: `from cv.theft_detection import
theft_service`) — أُبقيت بنفس الاسم للتوافق، لكن التنفيذ الفعلي انتقل الآن
إلى الوحدات المتخصصة الجديدة المدمجة من نسخة التطوير:

    cv/config.py        — كل الثوابت القابلة للتعديل (مناطق، عتبات، فئات)
    cv/detector.py       — غلاف YOLOv8 (نموذج مدرَّب مخصَّص best.pt) + MediaPipe Hands
    cv/zones.py          — هندسة المنطقتين (Scan Zone / Cart Zone)
    cv/tracker.py         — تتبّع الكائنات بين الإطارات (IoU) + علاقة اليد بالمنتج
    cv/scan_events.py    — تسجيل "متى حدث آخر مسح باركود" لكل جلسة
    cv/theft_logic.py     — طبقة القرار: PROLONGED_HOLDING / UNSCANNED_IN_CART

هذا الملف يُصدِّر فقط الأسماء التي يعتمد عليها بقية الباك اند
(`theft_service`, `TheftDetectionService`) حتى لا تحتاج main.py أو أي
مستورد آخر لأي تعديل.
"""
from cv.theft_logic import theft_service, TheftDetectionService  # noqa: F401
