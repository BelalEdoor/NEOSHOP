"""
cv/preview.py
=============
مخزن آخر إطار مُحلَّل + دالة الرسم لأداة معاينة الرؤية الحاسوبية (CV Preview).

⚠️ هذا الملف لا يشغّل YOLO ولا MediaPipe ولا Tracker ولا theft_logic من جديد.
فقط يُعيد استخدام النتائج (detections, tracked objects, pending state) التي
ينتجها cv/theft_logic.py::analyze_frame() أثناء تنفيذ خط الأنابيب الحقيقي
لكل إطار قادم من /ws/camera/{rfid}، ويرسم عليها overlay تصحيح أخطاء، ثم يخزّن
JPEG واحد فقط (آخر واحد) لكل session_id — جاهز ليُبثّ عبر routers/cv_preview.py.

Thread/asyncio-safety:
    - استبدال قيمة بقاموس تحت قفل خفيف (threading.Lock) — لا طابور غير
      محدود، ولا تراكم ذاكرة مهما طال البثّ. كل session_id يحتفظ بآخر
      إطار له فقط، فيُستبدَل تلقائياً بدل أن يتراكم.
    - القراءة (من مسار HTTP المستقل) لا تتداخل أبداً مع الكتابة (من مسار
      WebSocket + CV) لأن الاستبدال ذرّي (atomic reference swap).
"""
import threading
import time
from typing import Dict, Optional, Tuple

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════
# المخزن — إطار واحد (الأحدث) لكل جلسة
# ══════════════════════════════════════════════════════════════════════════
class _PreviewStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._frames: Dict[int, bytes] = {}
        self._updated_at: Dict[int, float] = {}
        self._latest_session_id: Optional[int] = None

    def publish(self, session_id: int, jpeg_bytes: bytes) -> None:
        with self._lock:
            self._frames[session_id] = jpeg_bytes
            self._updated_at[session_id] = time.time()
            self._latest_session_id = session_id

    def get(self, session_id: Optional[int] = None) -> Tuple[Optional[bytes], Optional[float]]:
        """
        session_id=None → آخر جلسة نُشر لها إطار (مفيد لفتح المعاينة مباشرة
        بدون معرفة رقم الجلسة). مررها صراحةً لمتابعة عربة معيّنة تحديداً.
        """
        with self._lock:
            sid = session_id if session_id is not None else self._latest_session_id
            if sid is None:
                return None, None
            return self._frames.get(sid), self._updated_at.get(sid)

    def active_sessions(self) -> list:
        with self._lock:
            return sorted(self._frames.keys())


preview_store = _PreviewStore()

_placeholder_cache: Optional[bytes] = None


def placeholder_jpeg() -> bytes:
    """
    صورة "بانتظار الكاميرا/CV" مولَّدة — تُستخدَم بدل نص عادي حتى يبقى نوع
    المحتوى image/jpeg ثابتاً طوال بثّ multipart/x-mixed-replace (خلط جزء
    نصّي وسط بثّ صور يكسر عرض <img> في بعض المتصفحات بشكل دائم للاتصال).
    تُبنى مرة واحدة فقط وتُخزَّن مؤقتاً (cache).
    """
    global _placeholder_cache
    if _placeholder_cache is not None:
        return _placeholder_cache
    if not CV2_AVAILABLE:
        return b""

    import numpy as np
    img = np.zeros((360, 640, 3), dtype="uint8")
    cv2.putText(img, "Waiting for camera / CV frame...", (30, 180),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    _placeholder_cache = buf.tobytes() if ok else b""
    return _placeholder_cache


# ══════════════════════════════════════════════════════════════════════════
# الرسم — يستهلك نفس الكائنات الناتجة عن خط الأنابيب الحقيقي فقط
# ══════════════════════════════════════════════════════════════════════════
def annotate_and_encode(frame, detections, tracked, pending, jpeg_quality: int = 80) -> Optional[bytes]:
    """
    frame:      إطار OpenCV الذي فك تشفيره theft_logic.py بالفعل لهذا الاستدعاء
                (لا يُفك تشفيره مرة ثانية هنا، ولا يُعدَّل النسخة الأصلية).
    detections: نفس ناتج Detector.detect() لهذا الإطار (منتجات + أيدٍ معاً).
    tracked:    نفس Dict[track_id, TrackedObject] من Tracker.get_tracked() —
                نفس الكائنات المستخدَمة فعلياً لاتخاذ قرار السرقة.
    pending:    نفس _PendingProduct الحالي لهذه الجلسة من theft_logic
                (أو None إن لم يوجد منتج معلّق حالياً) — "الحالة" المطلوبة.
    """
    if not CV2_AVAILABLE or frame is None:
        return None

    from cv import zones as _zones

    img = frame.copy()
    h, w = img.shape[:2]
    boundary = _zones.boundary_pixel_y(h)

    # ── حدود المنطقتين (Zone A / Zone B) ──────────────────────────────────
    cv2.line(img, (0, boundary), (w, boundary), (255, 255, 255), 2)
    cv2.putText(img, "Zone A - SCAN", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
    cv2.putText(img, "Zone B - CART", (10, boundary + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)

    # ── كل الاكتشافات الخام لهذا الإطار (منتجات صفراء، أيدٍ برتقالية) ──────
    for det in (detections or []):
        try:
            x1, y1, x2, y2 = map(int, det["xyxy"])
        except Exception:
            continue
        is_hand = det.get("category") == "hand"
        color = (255, 200, 0) if is_hand else (0, 255, 255)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)
        label_txt = f"{det.get('label', '?')} {det.get('conf', 0):.2f}"
        cv2.putText(img, label_txt, (x1, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    # ── الكائنات المتتبَّعة (بعد الـ Tracker) — لون حسب حالتها الفعلية ─────
    for obj in (tracked or {}).values():
        try:
            x1, y1, x2, y2 = map(int, obj.box)
        except Exception:
            continue
        if getattr(obj, "verified", False):
            color, state = (128, 128, 128), "verified"          # ممسوح، تم التحقق
        elif getattr(obj, "stable_in_cart", False):
            color, state = (0, 0, 255), "stable_in_cart"         # مستقرّ — قيد المراقبة
        elif getattr(obj, "in_cart_zone", False):
            color, state = (0, 165, 255), "in_cart_zone"         # دخل السلة، لسا مش مستقرّ
        else:
            color, state = (0, 255, 0), "tracked"                 # متتبَّع، خارج السلة
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, f"#{obj.track_id} {obj.label} [{state}]", (x1, min(h - 4, y2 + 16)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # ── حالة "المنتج المعلّق" الحالية من theft_logic (نفس القرار الحقيقي) ──
    if pending is not None:
        elapsed = time.time() - pending.placed_time
        state_val = getattr(pending.state, "value", str(pending.state))
        text = f"PENDING: {pending.label} (#{pending.track_id}) state={state_val} elapsed={elapsed:.1f}s"
        cv2.putText(img, text, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    else:
        cv2.putText(img, "PENDING: none", (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 2)

    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    return buf.tobytes() if ok else None