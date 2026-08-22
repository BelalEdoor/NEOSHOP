"""
cv/theft_logic.py
=================
Production-style theft monitoring flow for the graduation project.

سير العمل (بعد آخر تعديل جوهري — القرار يعتمد على "ذاكرة دائمة" للمنطقة
لكل جسم متتبَّع، وليس على مسك لحظة العبور بالضبط):

    1. الكاميرا على العربة تبثّ الإطارات للباك اند عبر WebSocket.
    2. Zone A (أعلى الإطار) = منطقة المسح. Zone B (أسفل الإطار) = السلة.
       هندسة المنطقتين نفسها لم تتغيّر إطلاقاً.
    3. ⚠️ كل جسم متتبَّع (cv/tracker.py::TrackedObject) يحتفظ بحقلين
       دائمين: `ever_seen_in_a` و`ever_seen_in_b` — يصيران True أول ما
       يُشاهَد الجسم بتلك المنطقة *ولو مرة واحدة*، ويبقيان True لبقية
       عمر الـ track بغضّ النظر عن الفريمات اللاحقة. هذا (بعكس
       `entered_cart`/`left_cart` اللحظيَّين القديمَين) متين تماماً أمام
       تخطّي الإطارات (`ANALYZE_EVERY_N_FRAMES`) — لا حاجة لتحليل كل فريم
       على حساب الأداء لمسك لحظة العبور بالضبط.
    4. ثلاث حالات فقط لفتح "فحص دخول" (obj.checked_entry يمنع التكرار):
       أ) شُوهد الجسم بمنطقة A سابقاً، وهو الآن بمنطقة B ➜ دخول طبيعي
          مؤكَّد — يُفتَح الفحص فوراً.
       ب) لم يُشاهَد أبداً بمنطقة A، لكنه استقرّ بمنطقة B فترة
          (`stable_in_cart`, نصف ثانية) دون حركة ➜ "دخل دون أن نراه
          يعبر" — يُعامَل كمرشّح سرقة، نفس فحص الدخول بالضبط.
       ج) لم يُشاهَد بمنطقة A، ولسا غير مستقرّ بمنطقة B ➜ لا شيء بعد،
          ننتظر (قد تكون يد عابرة أو حركة لم تكتمل).
    5. بعد فتح "منتج معلّق"، عدّاد الوقت (GRACE_PERIOD → WARNING →
       SCAN_TIMEOUT → ALARM) يعمل بالكامل على الزمن الفعلي، **بغضّ النظر
       عن استمرار ظهور الغرض بالفريم من عدمه**. اختفاء الغرض بصرياً بعد
       ذلك (دخل جوا السلة/الكيس فعلياً — أمر طبيعي ومتوقَّع) لا يُلغي
       التنبيه المعلَّق ولا يوقف العدّاد. الإلغاء الوحيد يصير عبر مسح
       باركود مطابق (try_consume)، أو فحص إرجاع لاحق (البند ٧ أدناه)، أو
       تصعيد فعلي للفرامل بعد انتهاء المهلة.
    6. فحص الفاتورة بنظام "استهلاك" غير حسّاس لترتيب الأحداث الزمني
       (receipt_monitor.try_consume) — يعمل سواء انمسح الباركود *قبل*
       العبور (مسح ثم وضع بالسلة) أو *بعده* (وضع بالسلة ثم مسح خلال
       المهلة). نجح فوراً ➜ أخضر، لا تنبيه. فشل ➜ GRACE_PERIOD (ثانيتان)
       صمتاً، ثم تحذير أصفر (SCAN_TIMEOUT=٨ث)، ثم PRODUCT_NOT_SCANNED
       (تفعيل فرامل + إشعار داشبورد + تسجيل قاعدة بيانات) إن لم يُستهلَك.
    7. فحص الإرجاع (_evaluate_pending_return_session) بنفس فلسفة الذاكرة
       الدائمة: أي جسم `ever_seen_in_b=True` (شُوهد بالسلة ولو مرة) وهو
       الآن بمنطقة A ولم يُفحَص كإرجاع بعد (`checked_return`) ➜ فحص
       "إرجاع" حصراً — بدون فرامل إطلاقاً، تحذير أصفر واحد بس إن لم
       يُحذَف من الفاتورة. وإن كان فيه فحص دخول مفتوح فعلياً لنفس الـ
       track لحظة هذا العبور، يُلغى بالكامل (تحذير/تصعيد) ويتحوّل كلياً
       لفحص الإرجاع فقط.

The tracker already provides the necessary cart interaction signals:
- track_id
- label
- in_cart_zone
- entered_cart          ← المُحفِّز الحالي (edge-triggered، مرة واحدة فقط)
- placed_in_cart / stable_in_cart   ← لم تعد تُستخدَم كمُحفِّز، فقط معلومة
  حالة إضافية (تُستخدَم بالمعاينة cv/preview.py لتلوين الصندوق فقط)
- last_seen

This service keeps only one pending product at a time and uses the
receipt monitor's consumption pool instead of the old scan-event logic.
"""
import asyncio
import logging
import time
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from cv import config as cv_config
from cv.receipt_monitor import receipt_monitor, _labels_match
from cv.tracker import Tracker
from cv.log_colors import colorize, CYAN, GREEN, YELLOW, RED

log = logging.getLogger("neoshop.cv")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log.warning("[CV] opencv-python not installed — frame analysis disabled")


class _PendingState(str, Enum):
    WAITING = "WAITING"
    WARNING = "WARNING"
    ALARM = "ALARM"


@dataclass
class _PendingProduct:
    """Represents one product that has entered the cart and is awaiting scan."""

    track_id: int
    label: str
    placed_time: float
    state: _PendingState = _PendingState.WAITING
    warning_started: Optional[float] = None
    warning_dispatched: bool = False
    alarm_sent: bool = False


@dataclass
class _PendingReturn:
    """
    منتج خرج من السلة (B→A — إرجاع/سحب) وبانتظار التأكد من حذفه فعلياً من
    الفاتورة. أبسط من _PendingProduct عمداً: لا تصعيد للفرامل هنا إطلاقاً
    (المطلوب تحذير أصفر فقط)، فمرحلة واحدة كافية: WAITING → WARNING مرة
    واحدة، ثم تُغلَق (بنجاح صامت أو بتحذير واحد لا يتكرر).
    """

    track_id: int
    label: str
    left_time: float
    warning_dispatched: bool = False


class TheftDetectionService:
    """Singleton responsible for pending-product scan enforcement."""

    def __init__(self):
        self._detector: Optional[Any] = None
        self._on_theft_detected: Optional[Callable] = None
        self._on_dashboard_alert: Optional[Callable] = None
        self._on_brake_callback: Optional[Callable] = None
        self._on_cleared_callback: Optional[Callable] = None
        self.tracker = Tracker()

        # session_id -> _PendingProduct
        self._pending_products: Dict[int, _PendingProduct] = {}
        # session_id -> _PendingReturn (منتج أُخرج من السلة، بانتظار تأكيد الحذف)
        self._pending_returns: Dict[int, _PendingReturn] = {}
        # session_id -> timestamp: لا تُفتح حلقة تنبيه جديدة قبل انقضاء التهدئة
        self._cooldown_until: Dict[int, float] = {}
        # session_id -> عدّاد إطارات، لتطبيق cv_config.ANALYZE_EVERY_N_FRAMES
        self._frame_counters: Dict[int, int] = {}
        # session_id -> {label: last_verified_timestamp} — يمنع إعادة فتح
        # تنبيه لنفس المنتج الفعلي لو الـ Tracker "خسر" الجسم وأعاد اكتشافه
        # بـ track_id جديد بعد لحظات (اهتزاز/انقطاع لحظي بالتتبّع، ليس منتجاً
        # ثانياً فعلياً) — راجع cv_config.RECENT_VERIFIED_WINDOW.
        self._recently_verified: Dict[int, Dict[str, float]] = {}
        # session_id -> منذ متى الكاميرا "مغطّاة" بشكل مستمر (None = صافية الآن)
        self._obstruction_since: Dict[int, Optional[float]] = {}
        # session_id -> timestamp: تهدئة بعد تنبيه تغطية سابق لنفس الجلسة
        self._obstruction_cooldown_until: Dict[int, float] = {}
        # session_id -> آخر مرة طُبع فيها لوق المعايرة (📊) — throttling بسيط
        self._obstruction_last_debug: Dict[int, float] = {}
        # session_id -> Counter({"bottle": 1, ...}) — كم قطعة من كل فئة
        # "مفروض" تكون بالسلة حالياً (على مستوى الجلسة، غير مرتبط بأي
        # track_id بعينه). يزيد لحظة تحقّق دخول ناجح، وينقص لحظة تحقّق
        # خروج/إرجاع. يُستخدَم كخط دفاع احتياطي: لو غرض فقد تتبّعه وهو
        # بالسلة ثم أُعيد اكتشافه بـ track_id جديد بمنطقة المسح (A)، لا
        # يوجد "تاريخ" لهذا الـ track الجديد يثبت أنه *كان* بالسلة —
        # فنعتمد هذا العدّاد بدل تتبّع الهوية الفردية.
        self._in_cart_count: Dict[int, Counter] = {}

    # ── Setup ─────────────────────────────────────────────────────────────
    def load_model(self):
        """Load the YOLO detector once at application startup."""
        from cv.detector import Detector
        try:
            self._detector = Detector()
        except Exception as exc:
            log.error(f"[CV] Failed to load YOLO model: {exc}")

    def set_theft_callback(self, callback: Callable):
        """Register the theft callback: callback(session_id, alert_dict)."""
        self._on_theft_detected = callback

    def set_dashboard_callback(self, callback: Callable):
        """Register the dashboard alert callback."""
        self._on_dashboard_alert = callback

    def set_brake_callback(self, callback: Callable):
        """Register the brake callback."""
        self._on_brake_callback = callback

    def set_cleared_callback(self, callback: Callable):
        """
        Register the "alert cleared" callback: callback(session_id).
        يُستدعى لحظة إلغاء تنبيه *سبق إرساله فعلاً* لنقطة البيع (وليس فقط
        منع فتح تنبيه جديد) — الحالة الوحيدة الحالية: منتج عبر A→B وفُتح
        له تحذير أصفر، ثم اتضح إنه مرّ مروراً سريعاً برّا (B→A) قبل أي
        تصعيد. بدون هذا الاستدعاء، شاشة التحذير تبقى ظاهرة عند العميل
        بلا داعٍ حتى ينتهي عدّها التنازلي من نفسه.
        """
        self._on_cleared_callback = callback

    @property
    def is_ready(self) -> bool:
        """هل نموذج YOLO محمَّل وجاهز؟ (يُستخدَم في /health)"""
        return self._detector is not None

    # ── Session management ───────────────────────────────────────────────
    def register_scanned_product(self, session_id: int, product_id: int, product_label: str = None):
        """
        Called by the POS when a barcode scan succeeds
        (routers/session.py::scan_product) — أي: أُضيف سطر جديد للفاتورة.

        product_label: تسمية عامة للمنتج (category أو name بقاعدة
        البيانات، مثال: "bottle") — تضاف كرصيد بمسبح الاستهلاك
        (receipt_monitor.register_scan)، بغضّ النظر عن توقيتها بالنسبة
        للعبور A→B (راجع رأس هذا الملف لتفاصيل نظام الاستهلاك).

        لو فيه "منتج معلّق" حالياً بنفس الفئة، نستهلك هذا المسح فوراً هنا
        (بدل انتظار دورة التقييم القادمة) ونمسح التنبيه على الفور — أسرع
        استجابة لنقطة البيع، ويمنع بقاء رصيد مكرَّر بالمسبح لنفس المسحة.
        """
        receipt_monitor.register_scan(session_id, product_label)
        self._mark_tracked_verified(session_id, matching_label=product_label)

        if not product_label:
            return

        pending = self._pending_products.get(session_id)
        if pending and _labels_match(product_label, pending.label):
            receipt_monitor.try_consume(session_id, product_label)
            self._clear_pending_product(session_id, matching_label=product_label)
            self._mark_recently_verified(session_id, product_label)
            self._in_cart_incr(session_id, product_label, +1)
            log.info(colorize(
                f"[CV] Session {session_id}: ✅ '{product_label}' scanned — "
                f"pending alert cleared immediately",
                GREEN, bold=True,
            ))

    def register_removed_product(self, session_id: int, product_id: int, product_label: str = None):
        """
        Called by the POS when a product is removed from the invoice
        (routers/session.py::remove_product) — أي: حُذف سطر من الفاتورة.

        نظير register_scanned_product بالضبط لكن باتجاه معاكس (مسبح
        "خروج" — راجع receipt_monitor.register_removal). لو فيه "منتج
        مُرجَع معلَّق" حالياً بنفس الفئة، نستهلك هذا الحذف فوراً ونمسح
        التحذير المعلَّق مباشرة.
        """
        receipt_monitor.register_removal(session_id, product_label)

        if not product_label:
            return

        pending = self._pending_returns.get(session_id)
        if pending and _labels_match(product_label, pending.label):
            receipt_monitor.try_consume_removal(session_id, product_label)
            self._pending_returns.pop(session_id, None)
            log.info(colorize(
                f"[CV] Session {session_id}: ✅ '{product_label}' removed from invoice — "
                f"return confirmed, pending cleared",
                GREEN, bold=True,
            ))

    def _mark_recently_verified(self, session_id: int, label: str):
        self._recently_verified.setdefault(session_id, {})[label.strip().lower()] = time.time()

    def _in_cart_incr(self, session_id: int, label: str, delta: int = 1):
        counter = self._in_cart_count.setdefault(session_id, Counter())
        key = label.strip().lower()
        counter[key] = max(0, counter[key] + delta)
        if counter[key] == 0:
            del counter[key]

    def _in_cart_has(self, session_id: int, label: str) -> bool:
        counter = self._in_cart_count.get(session_id)
        if not counter:
            return False
        needle = label.strip().lower()
        return any(_labels_match(needle, k) and v > 0 for k, v in counter.items())

    def _in_cart_consume_one(self, session_id: int, label: str) -> bool:
        """يُستهلَك رصيد واحد من العدّاد لو وُجد؛ يرجع True لو نقص فعلاً."""
        counter = self._in_cart_count.get(session_id)
        if not counter:
            return False
        needle = label.strip().lower()
        for k in list(counter.keys()):
            if counter[k] > 0 and _labels_match(needle, k):
                counter[k] -= 1
                if counter[k] <= 0:
                    del counter[k]
                return True
        return False

    def _was_recently_verified(self, session_id: int, label: str) -> bool:
        table = self._recently_verified.get(session_id)
        if not table:
            return False
        needle = label.strip().lower()
        now = time.time()
        for seen_label, ts in table.items():
            if now - ts > cv_config.RECENT_VERIFIED_WINDOW:
                continue
            if _labels_match(needle, seen_label):
                return True
        return False

    def acknowledge_session(self, session_id: int):
        """
        يُستدعى عندما يضغط الموظف زر "تفعيل السلة" بالداشبورد — أي أن
        المشكلة حُلّت يدوياً. يُصفّر الحالة المعلّقة ويعلّم كل ما هو
        متتبَّع الآن كـ verified حتى لا تُقفل العربة مباشرةً من جديد
        بسبب نفس المنتج الموجود أصلاً داخل السلة.
        """
        self._mark_tracked_verified(session_id)
        self._clear_pending_product(session_id)
        self._pending_returns.pop(session_id, None)
        self._cooldown_until[session_id] = time.time() + cv_config.ALERT_COOLDOWN

    def clear_session(self, session_id: int):
        """Clear all per-session tracking and pending state."""
        self.tracker.clear_session(session_id)
        receipt_monitor.reset(session_id)
        self._pending_products.pop(session_id, None)
        self._pending_returns.pop(session_id, None)
        self._cooldown_until.pop(session_id, None)
        self._frame_counters.pop(session_id, None)
        self._recently_verified.pop(session_id, None)
        self._obstruction_since.pop(session_id, None)
        self._obstruction_cooldown_until.pop(session_id, None)
        self._obstruction_last_debug.pop(session_id, None)
        self._in_cart_count.pop(session_id, None)

    def _mark_tracked_verified(self, session_id: int, matching_label: str = None):
        """
        matching_label=None (الحالة اليدوية: acknowledge_session) ➜ يُعلَّم
        كل الكائنات المتتبَّعة كـ verified بلا استثناء (تدخّل يدوي من
        الموظف يغطّي كل شيء بالسلة، بغضّ النظر عن نوعه).

        matching_label="bottle" (حالة مسح باركود فعلي) ➜ يُعلَّم فقط
        الكائنات التي تطابق هذه الفئة تحديداً. منتج آخر من فئة مختلفة
        ومعلَّق بانتظار المسح بنفس اللحظة يجب ألا يتأثر بمسح منتج غيره.
        """
        from cv.receipt_monitor import _labels_match
        for obj in self.tracker.get_tracked(session_id).values():
            if matching_label is None or _labels_match(matching_label, obj.label):
                obj.verified = True

    # ── Frame analysis (from a camera feed) ──────────────────────────────
    async def analyze_frame(
        self,
        frame_bytes: bytes,
        session_id: int,
        frame_height: int = 480,
    ) -> List[dict]:
        """Analyze one camera frame and return the new alerts for this frame."""
        if not self._detector or not CV2_AVAILABLE:
            return []

        # ── تخطّي إطارات لتخفيف حمل المعالج ─────────────────────────────────
        # عدّاد واحد لكل جلسة يُستخدَم لتحديد استحقاق كل من: كشف المنتجات
        # (cv_config.ANALYZE_EVERY_N_FRAMES — حرِج للقرار) وكشف اليد
        # (cv_config.HAND_ANALYZE_EVERY_N_FRAMES — تجميلي فقط، انظر detector.py).
        # لو ولا واحد منهم مستحق هالإطار، نتخطّى حتى فك تشفير JPEG بالكامل.
        # القرار مبني على الثواني لا على عدد الإطارات، فهذا لا يغيّر صحّة
        # القرار، فقط دقّته الزمنية (لا تزال أدق من اللازم بمراحل).
        count = self._frame_counters.get(session_id, 0) + 1
        self._frame_counters[session_id] = count

        run_products = count % max(1, cv_config.ANALYZE_EVERY_N_FRAMES) == 0
        run_hands = count % max(1, cv_config.HAND_ANALYZE_EVERY_N_FRAMES) == 0
        if not run_products and not run_hands:
            return []

        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return []

            # ── كشف تغطية الكاميرا (قماشة/يد أمام العدسة) — مستقل تماماً عن
            # منطق المنتجات، يعمل على كل إطار مفكوك بغضّ النظر عن run_products.
            self._check_camera_obstruction(session_id, frame)

            if run_products:
                detections = self._detector.detect(frame, run_products=True, run_hands=run_hands)
                alerts = self.update(session_id, detections, frame.shape[0])
            else:
                # إطار "يد فقط" — بدون كشف منتجات، فما في تغيير على الـ
                # tracker ولا على القرار (YOLO لا يُستدعى إطلاقاً هنا).
                detections = self._detector.detect(frame, run_products=False, run_hands=True)
                alerts = []

            self._publish_preview(session_id, frame, detections)
            return alerts
        except Exception as exc:
            log.error(f"[CV] Frame analysis error: {exc}")
            return []

    def _check_camera_obstruction(self, session_id: int, frame) -> None:
        """
        كشف تغطية متعمّدة للعدسة (قماشة/يد/سطح ملاصق) لمنع المراقبة.

        الفكرة: صورة الكاميرا الطبيعية (رفوف/منتجات/يد العميل) فيها تباين
        نسيجي واضح (تفاصيل، حواف، ألوان مختلفة). تغطية العدسة بالكامل
        بقماشة أو أي سطح قريب جداً تُنتج صورة شبه متجانسة اللون — انحراف
        معياري منخفض جداً لقنوات الرمادي. لو استمرّت هذه الحالة
        CAMERA_OBSTRUCTION_SECONDS (٣ ثوانٍ) متواصلة ➜ فرامل فورية، لأن
        تعطيل المراقبة عمداً مؤشر خطر بحدّ ذاته، بغضّ النظر عن وجود منتج
        معلَّق من عدمه.
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            std = float(gray.std())
        except Exception:
            return

        now = time.time()

        # 🔍 لوق تشخيصي/معايرة — يطبع القيمة الحية للانحراف المعياري كل
        # ثانية تقريباً (بغضّ النظر عن كونها أعلى أو أدنى من العتبة)، حتى
        # تقدر تشوف الأرقام الفعلية أثناء اختبار التغطية وتضبط
        # CAMERA_OBSTRUCTION_STD_THRESHOLD بـ cv/config.py حسب إضاءة موقعك
        # الحقيقية إن لم تكن ١٨.٠ الافتراضية مناسبة. احذف هذا السطر بعد
        # الانتهاء من المعايرة إن أردت تقليل ضجيج اللوق.

        if std >= cv_config.CAMERA_OBSTRUCTION_STD_THRESHOLD:
            # صورة طبيعية — تصفير أي حالة تغطية متراكمة
            self._obstruction_since.pop(session_id, None)
            return

        if now < self._obstruction_cooldown_until.get(session_id, 0.0):
            return  # صدر تنبيه تغطية مؤخراً لهذه الجلسة — تهدئة

        since = self._obstruction_since.get(session_id)
        if since is None:
            self._obstruction_since[session_id] = now
            return

        if now - since < cv_config.CAMERA_OBSTRUCTION_SECONDS:
            return

        # ── تغطية مستمرة لأكثر من المهلة ➜ فرامل فورية ──────────────────
        log.warning(colorize(
            f"[CV] Session {session_id}: 🎥🚫 Camera appears obstructed for "
            f"{int(cv_config.CAMERA_OBSTRUCTION_SECONDS)}s (std={std:.1f}) — activating brakes",
            RED, bold=True,
        ))
        alert = self._build_obstruction_alert(session_id)
        self._dispatch_theft_alert(session_id, alert)
        self._dispatch_dashboard_alert(session_id, alert)
        self._dispatch_brake(session_id, alert)

        self._obstruction_since.pop(session_id, None)
        self._obstruction_cooldown_until[session_id] = now + cv_config.ALERT_COOLDOWN

    def _build_obstruction_alert(self, session_id: int) -> dict:
        return {
            "alert_type": "CAMERA_OBSTRUCTED",
            "trigger": "camera_obstruction",
            "confidence_score": 1.0,
            "track_id": None,
            "object_class": None,
            "description": (
                f"Camera view has been obstructed for more than "
                f"{int(cv_config.CAMERA_OBSTRUCTION_SECONDS)} seconds — possible attempt to "
                f"disable surveillance."
            ),
            "session_id": session_id,
            "zone": None,
            "grace_seconds": None,
            "brake_activated": True,
        }

    def _publish_preview(self, session_id: int, frame, detections: List[dict]) -> None:
        """
        أداة معاينة CV (Debug) — routers/cv_preview.py::/cv/preview.
        تعيد استخدام frame/detections المحسوبة أعلاه بالضبط + tracked/pending
        الحاليين بعد update()، بدون أي استدلال إضافي (لا YOLO ولا MediaPipe
        ولا Tracker جديد). فاشلة بصمت إن حدث أي خطأ حتى لا تؤثر على خط
        الأنابيب الحقيقي (كشف السرقة يبقى يعمل حتى لو تعطّلت المعاينة).
        """
        try:
            from cv.preview import preview_store, annotate_and_encode
            tracked = self.tracker.get_tracked(session_id)
            pending = self._pending_products.get(session_id)
            jpeg = annotate_and_encode(frame, detections, tracked, pending)
            if jpeg:
                preview_store.publish(session_id, jpeg)
        except Exception as exc:
            # كانت log.debug (مخفية بمستوى INFO الافتراضي) فصار مستحيل تشخيص
            # لماذا المعاينة فاضية رغم أن الإطارات تُعالَج فعلياً. warning +
            # exc_info تضمن ظهور السبب الحقيقي باللوق العادي دون كسر خط
            # الأنابيب الأساسي (لا يزال هذا الاستثناء لا يوقف تحليل السرقة).
            log.warning(f"[CV] preview publish failed (session {session_id}): {exc}", exc_info=True)

    # ── Direct pipeline entrypoint (frame already detected elsewhere) ────
    def update(self, session_id: int, detections: List[dict], frame_height: int) -> List[dict]:
        """Update tracker state and evaluate the pending scan + return workflows."""
        self.tracker.update(session_id, detections, frame_height)
        alerts = self._evaluate_pending_session(session_id)
        alerts += self._evaluate_pending_return_session(session_id)
        return alerts

    def _open_entry_check(self, session_id: int, obj, now: float):
        """
        يفتح فحص الدخول الفعلي (عبور مؤكَّد A→B مباشرة، أو دخول سريع تأكَّد
        بعد نافذة المراقبة) — مُستخرَجة بدالة مستقلة ليُعاد استخدامها من
        كلا المسارين بدل تكرار نفس المنطق مرتين.
        يرجع obj لو فُتح تنبيه أو انحلّ فوراً (✅)، أو None لو تم تجاوزه
        (تحقّق حديثاً لنفس الفئة).
        """
        if self._was_recently_verified(session_id, obj.label):
            obj.verified = True
            log.info(colorize(
                f"[CV] Session {session_id}: 🔁 '{obj.label}' re-detected "
                f"(track #{obj.track_id}) — already verified recently, ignoring",
                CYAN,
            ))
            return None

        log.info(colorize(
            f"[CV] Session {session_id}: 🚶 CROSSED A→B — "
            f"product: {obj.label} | accuracy: {getattr(obj, 'conf', 0.0):.2f} (track #{obj.track_id})",
            CYAN, bold=True,
        ))
        log.info(colorize(
            f"[CV] Session {session_id}: 🔍 Checking invoice for '{obj.label}'...",
            CYAN,
        ))

        if receipt_monitor.try_consume(session_id, obj.label):
            obj.verified = True
            self._mark_recently_verified(session_id, obj.label)
            self._in_cart_incr(session_id, obj.label, +1)
            log.info(colorize(
                f"[CV] Session {session_id}: ✅ '{obj.label}' was added to the "
                f"invoice correctly — no action needed",
                GREEN, bold=True,
            ))
            return obj

        self._pending_products[session_id] = _PendingProduct(
            track_id=obj.track_id,
            label=obj.label,
            placed_time=now,
        )
        return obj

    # ── Pending scan workflow ────────────────────────────────────────────
    def _evaluate_pending_session(self, session_id: int) -> List[dict]:
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        pending = self._pending_products.get(session_id)
        alerts: List[dict] = []

        # ── فتح فحص دخول جديد — بالاعتماد على "ذاكرة المنطقة" الدائمة ──────
        # (ever_seen_in_a/stable_in_cart) بدل اللحظة الآنية entered_cart —
        # متين أمام تخطّي الإطارات (ANALYZE_EVERY_N_FRAMES)، ما بيحتاج نمسك
        # فريم العبور بالظبط. ثلاث حالات فقط (بالضبط كما طُلب):
        #
        #   ١) شُوهد بمنطقة A سابقاً، وهلق بمنطقة B ➜ دخول طبيعي مؤكَّد.
        #      (يفتح الفحص فوراً — لا داعي للانتظار، الدليل قوي أصلاً.)
        #   ٢) لم يُشاهَد أبداً بمنطقة A، لكنه استقرّ بمنطقة B ولم يتحرّك
        #      لفترة (stable_in_cart) ➜ دخل دون أن نراه بمنطقة A — يُعامَل
        #      كمرشّح سرقة (نفس فحص الدخول العادي بالضبط).
        #   ٣) لم يُشاهَد بمنطقة A، ولسا غير مستقرّ بمنطقة B (احتمال يد
        #      عابرة أو حركة لسا بالمنتصف) ➜ ننتظر، لا فحص بعد.
        if pending is None:
            if now < self._cooldown_until.get(session_id, 0.0):
                return alerts

            for obj in tracked.values():
                if getattr(obj, "verified", False):
                    continue
                if getattr(obj, "checked_entry", False):
                    continue  # سبق فحص هذا الـ track — لا تكرار
                if not getattr(obj, "in_cart_zone", False):
                    continue  # مو داخل Zone B حالياً أصلاً

                seen_in_a = getattr(obj, "ever_seen_in_a", False)
                settled = getattr(obj, "stable_in_cart", False)

                if not seen_in_a and not settled:
                    continue  # (٣) لسا مبكر — انتظر دورة تالية

                # ── قمع إعادة الفتح لنفس المنتج الفعلي ─────────────────
                # لو نفس الفئة اتحقّقت (✅) خلال آخر RECENT_VERIFIED_WINDOW
                # ثانية لهذه الجلسة، هذا على الأغلب نفس الغرض الفعلي أعاد
                # الـ Tracker اكتشافه بـ track_id جديد (اهتزاز/انقطاع لحظي
                # بالتتبّع) — وليس منتجاً ثانياً حقيقياً عبر لتوّه. تجاهله
                # بصمت بدل فتح تنبيه زائف على منتج مُتحقَّق منه أصلاً.
                if self._was_recently_verified(session_id, obj.label):
                    obj.verified = True
                    obj.checked_entry = True
                    log.info(colorize(
                        f"[CV] Session {session_id}: 🔁 '{obj.label}' re-detected "
                        f"(track #{obj.track_id}) — already verified recently, ignoring",
                        CYAN,
                    ))
                    continue

                if not seen_in_a:
                    log.info(colorize(
                        f"[CV] Session {session_id}: 🕵️ '{obj.label}' (track #{obj.track_id}) "
                        f"settled in Zone B without ever being seen in Zone A — "
                        f"treating as a theft candidate",
                        CYAN, bold=True,
                    ))

                obj.checked_entry = True
                result = self._open_entry_check(session_id, obj, now)
                if result is not None:
                    break

            return alerts

        if pending is None:
            return alerts

        # ── ⚠️ التغيير الجوهري: مجرّد العبور يكفي لبدء العدّاد — ما بعده
        # لا يعتمد إطلاقاً على بقاء الغرض ظاهراً بالفريم. سابقاً كان فقدان
        # الـ track (الغرض دخل جوا السلة/الكيس واختفى عن YOLO — وهو أمر
        # طبيعي ومتوقَّع تماماً بعد وضع أي منتج بالسلة فعلياً) يُلغي التنبيه
        # المعلَّق فوراً، فتتوقف دورة (تحذير → فرامل) بمنتصف الطريق كل مرة.
        # الآن: العدّاد (GRACE_PERIOD → WARNING → SCAN_TIMEOUT → ALARM) يعمل
        # بالكامل على الزمن الفعلي (time.time())، بغضّ النظر عن استمرار
        # ظهور الغرض بالفريم من عدمه — تماماً كما يحدث بالواقع الفعلي.
        tracked_obj = tracked.get(pending.track_id)  # قد يكون None، وهذا متوقَّع وسليم

        # ── إعادة محاولة الاستهلاك في كل تقييم لاحق — يلتقط مسحاً وصل
        # بعد لحظة العبور (العميل وضع المنتج بالسلة ثم مسحه خلال المهلة) ──
        if receipt_monitor.try_consume(session_id, pending.label):
            if tracked_obj is not None:
                tracked_obj.verified = True
            self._mark_recently_verified(session_id, pending.label)
            self._in_cart_incr(session_id, pending.label, +1)
            self._clear_pending_product(session_id, matching_label=pending.label)
            log.info(colorize(
                f"[CV] Session {session_id}: ✅ '{pending.label}' was added to the "
                f"invoice correctly — pending cleared, situation normal",
                GREEN, bold=True,
            ))
            return alerts

        if pending.state == _PendingState.WAITING:
            if now - pending.placed_time < cv_config.GRACE_PERIOD:
                return alerts

            pending.state = _PendingState.WARNING
            pending.warning_started = now
            alert = self._build_warning_alert(session_id, pending)
            alerts.append(alert)

            # يُرسَل مرة واحدة فقط لكل حلقة — لا نغرق نقطة البيع بتحذير لكل إطار
            if not pending.warning_dispatched:
                pending.warning_dispatched = True
                log.info(colorize(
                    f"[CV] Session {session_id}: ⚠️ '{pending.label}' NOT found on invoice — "
                    f"issuing warning (PLEASE_SCAN_PRODUCT)...",
                    YELLOW, bold=True,
                ))
                self._dispatch_theft_alert(session_id, alert)
                self._dispatch_dashboard_alert(session_id, alert)
            return alerts

        if pending.state == _PendingState.WARNING:
            alerts.append(self._build_warning_alert(session_id, pending))

            if pending.alarm_sent:
                return alerts

            if now - pending.warning_started < cv_config.SCAN_TIMEOUT:
                return alerts

            # ── انتهت مهلة الـ ٨ ثوانٍ دون مسح ➜ تصعيد ────────────────────
            pending.state = _PendingState.ALARM
            pending.alarm_sent = True
            if tracked_obj is not None:
                tracked_obj.verified = True  # لا تُعِد إطلاق نفس الإنذار لنفس الجسم لو لسا ظاهر
            # الغرض فعلياً بالسلة رغم عدم الدفع — لو أُخرج لاحقاً بدون حذفه
            # من الفاتورة (وهو أصلاً غير موجود بالفاتورة) نريد أن يُكتشَف
            # أيضاً عبر نفس آلية "خروج بدون حذف مطابق".
            self._in_cart_incr(session_id, pending.label, +1)

            log.warning(colorize(
                f"[CV] Session {session_id}: 🚨 '{pending.label}' still not scanned after "
                f"{int(cv_config.SCAN_TIMEOUT)}s — activating brakes",
                RED, bold=True,
            ))

            alert = self._build_theft_alert(session_id, pending)
            self._dispatch_theft_alert(session_id, alert)
            self._dispatch_dashboard_alert(session_id, alert)
            self._dispatch_brake(session_id, alert)

            self._clear_pending_product(session_id)
            self._cooldown_until[session_id] = time.time() + cv_config.ALERT_COOLDOWN
            alerts.append(alert)

        return alerts

    # ── Pending RETURN workflow (B→A — منتج أُخرج من السلة) ────────────────
    def _evaluate_pending_return_session(self, session_id: int) -> List[dict]:
        """
        نظير _evaluate_pending_session لكن باتجاه معاكس: عبور B→A
        (`obj.left_cart`) بدل A→B. لا فرامل هنا إطلاقاً بالتصميم — تحذير
        أصفر واحد فقط إن لم يُحذف المنتج من الفاتورة خلال RETURN_GRACE_PERIOD.
        """
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        pending = self._pending_returns.get(session_id)
        alerts: List[dict] = []

        if pending is None:
            # ── ⚠️ إشارة إرجاع مستهدَفة (جديدة، أضيق من المسار القديم
            # المحذوف): لو فيه "فحص دخول" مفتوح فعلياً حالياً (منتج عبر
            # A→B ولسا ما انحلّ)، وظهر track **جديد كلياً** بمنطقة A بنفس
            # الفئة تحديداً — هذا سياق قوي وموثوق (مش تخمين عام كالمسار
            # القديم): على الأغلب نفس الغرض "المفقود" (فقدت الكاميرا
            # تتبّعه أثناء إخراجه بسرعة، فأعاد الـ Tracker اكتشافه بـ
            # track_id جديد بمنطقة المسح). بعكس المسار القديم المحذوف
            # (كان يفحص أي رصيد تاريخي "بالسلة" لأي غرض ثانٍ)، هذا مقيَّد
            # حصراً بوجود فحص دخول *مفتوح الآن* لنفس الفئة — فلا يتأثر
            # بشراء قطعة ثانية شرعية من نفس الصنف (حالة لا يوجد لها فحص
            # دخول معلَّق أصلاً وقت ظهورها).
            entry_pending = self._pending_products.get(session_id)
            if entry_pending is not None:
                for obj in tracked.values():
                    if (
                        getattr(obj, "just_created", False)
                        and not getattr(obj, "in_cart_zone", True)
                        and _labels_match(obj.label, entry_pending.label)
                    ):
                        log.info(colorize(
                            f"[CV] Session {session_id}: 🔎 '{obj.label}' (track #{obj.track_id}) "
                            f"re-appeared in Zone A matching the currently-open entry-check for "
                            f"'{entry_pending.label}' — treating as the same item being returned, "
                            f"cancelling entry-check, switching to return-check",
                            CYAN,
                        ))
                        if entry_pending.warning_dispatched:
                            self._dispatch_cleared(session_id)
                        self._clear_pending_product(session_id)

                        log.info(colorize(
                            f"[CV] Session {session_id}: 🔍 Checking invoice for removal of "
                            f"'{obj.label}'...",
                            CYAN,
                        ))
                        self._in_cart_consume_one(session_id, obj.label)

                        if receipt_monitor.try_consume_removal(session_id, obj.label):
                            log.info(colorize(
                                f"[CV] Session {session_id}: ✅ '{obj.label}' removal matched on "
                                f"invoice — situation normal",
                                GREEN, bold=True,
                            ))
                        else:
                            self._pending_returns[session_id] = _PendingReturn(
                                track_id=obj.track_id,
                                label=obj.label,
                                left_time=now,
                            )
                        return alerts

            for obj in tracked.values():
                # ── ⚠️ المُحفِّز صار "ذاكرة دائمة" بدل اللحظة الآنية: أي
                # جسم شُوهد بمنطقة B (ولو مرة واحدة، بأي وقت خلال عمر هذا
                # الـ track) وهلق موجود بمنطقة A ولم يُفحَص كإرجاع من قبل
                # — بغضّ النظر عن كون فريم لحظة العبور بالضبط قد حُلِّل أو
                # لأ (متين أمام تخطّي الإطارات ANALYZE_EVERY_N_FRAMES).
                if getattr(obj, "checked_return", False):
                    continue
                if getattr(obj, "in_cart_zone", True):
                    continue  # لسا بمنطقة B، مو بـA
                if not getattr(obj, "ever_seen_in_b", False):
                    continue  # ما كان بالسلة أبداً — لا علاقة له بالإرجاع

                obj.checked_return = True

                # ── ⚠️ لو نفس هذا الـ track كان له "فحص دخول" معلَّق (فتحناه
                # سابقاً لحظة عبوره A→B) ولسا ما انحلّ، وهلق طلع إنه عبر فوراً
                # برّا (B→A) — يعني الغرض مرّ مروراً سريعاً بالسلة ولم يستقرّ
                # فعلياً فيها. بهذه الحالة لا داعي إطلاقاً لفحص "هل أُضيف
                # للفاتورة" (منطق الدخول) — نُلغيه بالكامل بصمت (بدون أي
                # تحذير/فرامل) ونكتفي بفحص "هل حُذف من الفاتورة" (منطق
                # الإرجاع) فقط، لأنه هذا بالضبط سيناريو "شافه في B ومرّ لA
                # مباشرة: ما في أي مشكلة، بس افحص لوجيك الإرجاع".
                entry_pending = self._pending_products.get(session_id)
                if entry_pending is not None and entry_pending.track_id == obj.track_id:
                    log.info(colorize(
                        f"[CV] Session {session_id}: ↩️ '{obj.label}' (track #{obj.track_id}) "
                        f"passed through to Zone A before settling — cancelling entry-check, "
                        f"switching fully to return-check",
                        CYAN,
                    ))
                    # لو كان تحذير أصفر قد وصل فعلاً لنقطة البيع (warning_dispatched)
                    # قبل ما نكتشف هذا العبور، لازم نُعلِم الواجهة إنه انحلّ —
                    # وإلا تبقى شاشة التحذير ظاهرة للعميل بلا داعٍ حتى تنتهي
                    # مهلتها من نفسها (٨ ثوانٍ) رغم أن لا مشكلة فعلياً.
                    if entry_pending.warning_dispatched:
                        self._dispatch_cleared(session_id)
                    self._clear_pending_product(session_id)

                log.info(colorize(
                    f"[CV] Session {session_id}: 🚶 CROSSED B→A (returned) — "
                    f"product: {obj.label} | accuracy: {getattr(obj, 'conf', 0.0):.2f} (track #{obj.track_id})",
                    CYAN, bold=True,
                ))
                log.info(colorize(
                    f"[CV] Session {session_id}: 🔍 Checking invoice for removal of '{obj.label}'...",
                    CYAN,
                ))

                # الغرض عمليّاً خرج من السلة (بالطريقتين) — يُستهلَك من
                # عدّاد "بالسلة" فوراً هون، بغضّ النظر عن نتيجة فحص الفاتورة.
                self._in_cart_consume_one(session_id, obj.label)

                # استهلاك فوري — يلتقط حذفاً صار قبل أو بعد الإخراج فعلياً
                if receipt_monitor.try_consume_removal(session_id, obj.label):
                    log.info(colorize(
                        f"[CV] Session {session_id}: ✅ '{obj.label}' removal matched on "
                        f"invoice — situation normal",
                        GREEN, bold=True,
                    ))
                    continue

                self._pending_returns[session_id] = _PendingReturn(
                    track_id=obj.track_id,
                    label=obj.label,
                    left_time=now,
                )
                pending = self._pending_returns[session_id]
                break

        if pending is None:
            return alerts

        # نفس فلسفة سير عمل الدخول: العدّاد يعمل بالزمن الفعلي، بغضّ النظر
        # عن استمرار ظهور الغرض بالفريم من عدمه.
        if receipt_monitor.try_consume_removal(session_id, pending.label):
            self._pending_returns.pop(session_id, None)
            log.info(colorize(
                f"[CV] Session {session_id}: ✅ '{pending.label}' removal matched on "
                f"invoice — pending cleared, situation normal",
                GREEN, bold=True,
            ))
            return alerts

        if now - pending.left_time < cv_config.RETURN_GRACE_PERIOD:
            return alerts

        if not pending.warning_dispatched:
            pending.warning_dispatched = True
            log.warning(colorize(
                f"[CV] Session {session_id}: ⚠️ '{pending.label}' was taken out of the cart "
                f"but NOT removed from the invoice — issuing warning (no brake)",
                YELLOW, bold=True,
            ))
            alert = self._build_return_warning_alert(session_id, pending)
            self._dispatch_theft_alert(session_id, alert)
            self._dispatch_dashboard_alert(session_id, alert)
            alerts.append(alert)
            # تحذير واحد فقط ثم إغلاق — لا تصعيد ولا نطارد نفس الحالة للأبد
            self._pending_returns.pop(session_id, None)

        return alerts

    def _build_return_warning_alert(self, session_id: int, pending: _PendingReturn) -> dict:
        return {
            "alert_type": "ITEM_RETURNED_NOT_REMOVED",
            "trigger": "return_not_removed",
            "confidence_score": 0.6,
            "track_id": pending.track_id,
            "object_class": pending.label,
            "description": (
                f"Product ({pending.label}) was taken out of the cart but was not "
                f"removed from the invoice."
            ),
            "session_id": session_id,
            "zone": "Scan",
            "grace_seconds": None,   # توست بسيط بدل عدّاد تنازلي — ليست حالة تصعيد
            "brake_activated": False,
        }

    def _build_warning_alert(self, session_id: int, pending: _PendingProduct) -> dict:
        elapsed = time.time() - (pending.warning_started or time.time())
        return {
            "alert_type": "PLEASE_SCAN_PRODUCT",
            "trigger": "pending_scan",
            "confidence_score": 0.6,
            "track_id": pending.track_id,
            "object_class": pending.label,
            "description": f"Product ({pending.label}) placed in cart — please scan it.",
            "session_id": session_id,
            "zone": "Cart",
            # مدة العدّ التنازلي على شاشة نقطة البيع (٨ ثوانٍ)
            "grace_seconds": cv_config.SCAN_TIMEOUT,
            "seconds_remaining": max(0.0, round(cv_config.SCAN_TIMEOUT - elapsed, 1)),
            "brake_activated": False,
        }

    def _build_theft_alert(self, session_id: int, pending: _PendingProduct) -> dict:
        return {
            "alert_type": "PRODUCT_NOT_SCANNED",
            "trigger": "scan_timeout",
            "confidence_score": 1.0,
            "track_id": pending.track_id,
            "object_class": pending.label,
            "description": (
                f"Product ({pending.label}) was placed in cart and not scanned "
                f"within {int(cv_config.SCAN_TIMEOUT)} seconds."
            ),
            "session_id": session_id,
            "zone": "Cart",
            "grace_seconds": None,
            "brake_activated": True,
        }

    def _dispatch_theft_alert(self, session_id: int, alert: dict):
        if self._on_theft_detected:
            self._schedule(self._on_theft_detected(session_id, alert))
        else:
            log.warning("[CV] No theft callback registered; skipping theft alert dispatch")

    def _dispatch_dashboard_alert(self, session_id: int, alert: dict):
        if self._on_dashboard_alert:
            self._schedule(self._on_dashboard_alert(session_id, alert))
        else:
            log.warning("[CV] Dashboard alert callback not configured")

    def _dispatch_cleared(self, session_id: int):
        if self._on_cleared_callback:
            self._schedule(self._on_cleared_callback(session_id))

    def _dispatch_brake(self, session_id: int, alert: dict):
        if self._on_brake_callback:
            self._schedule(self._on_brake_callback(session_id, alert))
        else:
            log.warning("[CV] Brake callback not configured")

    @staticmethod
    def _schedule(coro):
        """
        تشغيل الـ callback بأمان. update() قد تُستدعى من سياق متزامن
        (webcam_test.py مثلاً) حيث لا يوجد event loop شغّال، فيرمي
        asyncio.create_task استثناء RuntimeError ويُسقط التحليل كله.
        """
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            coro.close()
            log.debug("[CV] No running event loop — alert callback skipped (offline mode)")

    def _clear_pending_product(self, session_id: int, matching_label: str = None):
        """
        matching_label=None ➜ يُلغى المعلَّق الحالي لهذه الجلسة بلا شرط
        (acknowledge_session اليدوي، أو حالات داخلية أخرى كانت تُلغي دائماً).

        matching_label="bottle" ➜ يُلغى فقط لو كان المنتج المعلَّق حالياً
        من نفس الفئة الممسوحة. لو فيه منتج آخر معلَّق من فئة مختلفة، يبقى
        كما هو — مسح "bottle" لا يجوز أن يُسقِط تنبيهاً معلَّقاً على "chips".
        """
        pending = self._pending_products.get(session_id)
        if pending is None:
            return
        if matching_label is None:
            self._pending_products.pop(session_id, None)
            return
        from cv.receipt_monitor import _labels_match
        if _labels_match(matching_label, pending.label):
            self._pending_products.pop(session_id, None)

    @property
    def has_pending(self) -> bool:
        """Return True when at least one pending product exists for any session."""
        return len(self._pending_products) > 0

    def has_pending_for(self, session_id: int) -> bool:
        """
        نظير has_pending لكن لجلسة محدَّدة فقط — has_pending العامة كانت
        تتحقق عبر كل الجلسات النشطة معاً، وهو غير دقيق عند استخدامه من
        alert_handler.py::_poll_invoice_and_clear_early لمعرفة "هل لسا
        فيه تنبيه معلَّق لنفس هذه الجلسة تحديداً".
        """
        return session_id in self._pending_products


# ── Singleton ─────────────────────────────────────────────────────────────
theft_service = TheftDetectionService()