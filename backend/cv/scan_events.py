"""
cv/scan_events.py
=================
واجهة "تم تسجيل مسح" قابلة للربط. طبقة الرؤية الحاسوبية لا تعرف ولا تهتم
بكيفية حدوث المسح (باركود، RFID، إدخال يدوي) — تحتاج فقط أن تعرف أن مسحاً
حدث لهذه الجلسة، ومتى.

نقطة الربط الحقيقية: routers/session.py::scan_product يستدعي
`register_scan_event(session_id, product_id)` بعد كل عملية مسح باركود ناجحة.

الحالة محفوظة لكل جلسة (session_id) وليست عالمية، لأن عدة عربات تعمل بشكل
متزامن في هذا النظام.
"""
import threading
import time
from typing import Dict, Optional

_lock = threading.Lock()
_last_scan_timestamp: Dict[int, float] = {}


def register_scan_event(session_id: int, product_id: Optional[int] = None):
    """يُستدعى فور تأكيد مسح باركود/RFID لهذه الجلسة."""
    with _lock:
        _last_scan_timestamp[session_id] = time.time()


def has_recent_scan(session_id: int, window_seconds: float) -> bool:
    """صحيح إذا سُجِّل مسح لهذه الجلسة خلال آخر `window_seconds` ثانية."""
    with _lock:
        ts = _last_scan_timestamp.get(session_id)
        if ts is None:
            return False
        return (time.time() - ts) <= window_seconds


def seconds_since_last_scan(session_id: int) -> Optional[float]:
    with _lock:
        ts = _last_scan_timestamp.get(session_id)
        if ts is None:
            return None
        return time.time() - ts


def clear_session(session_id: int):
    """تنظيف حالة الجلسة عند انتهاء التسوق."""
    with _lock:
        _last_scan_timestamp.pop(session_id, None)
