"""
cv/theft_logic.py
=================
Production-style theft monitoring flow for the graduation project.

سير العمل (كما هو مطلوب من النظام):
    1. الكاميرا على العربة تبثّ الإطارات للباك اند عبر WebSocket.
    2. Zone A (أعلى الإطار) = منطقة المسح — لا قرارات تُتّخذ فيها.
    3. Zone B (أسفل الإطار) = السلة — هنا يحدث التتبّع والقرار.
    4. منتج استقرّ داخل Zone B  ➜  يبدأ "منتج معلّق" (pending) وتُثبَّت
       نسخة الفاتورة الحالية كنقطة مرجعية.
    5. تُراقَب الفاتورة باستمرار: إن أُضيف سطر جديد (مسح باركود) ➜ يُلغى
       التنبيه ويُعتبر المنتج مدفوعاً.
    6. لم يُمسح خلال GRACE_PERIOD ➜ تحذير أحمر على نقطة البيع مدته
       SCAN_TIMEOUT (٨ ثوانٍ) يطلب إعادة مسح المنتج.
    7. انتهت الثواني الثمانية دون مسح ➜ إنذار PRODUCT_NOT_SCANNED:
       - أمر تفعيل الفرامل يُرسَل للراسبيري باي (٤ سيرفوهات).
       - إشعار للداشبورد مع زر "تفعيل السلة".
       - تسجيل الحالة بقاعدة البيانات.

The tracker already provides the necessary cart interaction signals:
- track_id
- label
- in_cart_zone
- entered_cart
- placed_in_cart / stable_in_cart
- last_seen

This service keeps only one pending product at a time and uses the
receipt monitor instead of the old scan-event logic.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from cv import config as cv_config
from cv.receipt_monitor import receipt_monitor
from cv.tracker import Tracker
from cv.log_colors import colorize, CYAN

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


class TheftDetectionService:
    """Singleton responsible for pending-product scan enforcement."""

    def __init__(self):
        self._detector: Optional[Any] = None
        self._on_theft_detected: Optional[Callable] = None
        self._on_dashboard_alert: Optional[Callable] = None
        self._on_brake_callback: Optional[Callable] = None
        self.tracker = Tracker()

        # session_id -> _PendingProduct
        self._pending_products: Dict[int, _PendingProduct] = {}
        # session_id -> timestamp: لا تُفتح حلقة تنبيه جديدة قبل انقضاء التهدئة
        self._cooldown_until: Dict[int, float] = {}
        # session_id -> عدّاد إطارات، لتطبيق cv_config.ANALYZE_EVERY_N_FRAMES
        self._frame_counters: Dict[int, int] = {}

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

    @property
    def is_ready(self) -> bool:
        """هل نموذج YOLO محمَّل وجاهز؟ (يُستخدَم في /health)"""
        return self._detector is not None

    # ── Session management ───────────────────────────────────────────────
    def register_scanned_product(self, session_id: int, product_id: int):
        """
        Called by the POS when a barcode scan succeeds
        (routers/session.py::scan_product) — أي: أُضيف سطر جديد للفاتورة.

        بما أنه لا يمكن ربط الباركود الممسوح بصندوق YOLO بعينه، نعتبر أن
        المسح يُغطّي المنتجات المتتبَّعة حالياً داخل السلة: تُعلَّم كـ
        verified فلا تُعيد إطلاق نفس التنبيه إلى ما لا نهاية.
        """
        receipt_monitor.register_scan(session_id)
        self._mark_tracked_verified(session_id)
        self._clear_pending_product(session_id)

    def acknowledge_session(self, session_id: int):
        """
        يُستدعى عندما يضغط الموظف زر "تفعيل السلة" بالداشبورد — أي أن
        المشكلة حُلّت يدوياً. يُصفّر الحالة المعلّقة ويعلّم كل ما هو
        متتبَّع الآن كـ verified حتى لا تُقفل العربة مباشرةً من جديد
        بسبب نفس المنتج الموجود أصلاً داخل السلة.
        """
        self._mark_tracked_verified(session_id)
        self._clear_pending_product(session_id)
        receipt_monitor.checkpoint(session_id)
        self._cooldown_until[session_id] = time.time() + cv_config.ALERT_COOLDOWN

    def clear_session(self, session_id: int):
        """Clear all per-session tracking and pending state."""
        self.tracker.clear_session(session_id)
        receipt_monitor.reset(session_id)
        self._pending_products.pop(session_id, None)
        self._cooldown_until.pop(session_id, None)
        self._frame_counters.pop(session_id, None)

    def _mark_tracked_verified(self, session_id: int):
        for obj in self.tracker.get_tracked(session_id).values():
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
        """Update tracker state and evaluate the pending scan workflow."""
        self.tracker.update(session_id, detections, frame_height)
        return self._evaluate_pending_session(session_id)

    # ── Pending scan workflow ────────────────────────────────────────────
    def _evaluate_pending_session(self, session_id: int) -> List[dict]:
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        pending = self._pending_products.get(session_id)
        alerts: List[dict] = []

        # ── فتح حلقة تنبيه جديدة: أول منتج غير مُتحقَّق منه استقرّ في Zone B ──
        if pending is None:
            if now < self._cooldown_until.get(session_id, 0.0):
                return alerts

            for obj in tracked.values():
                if getattr(obj, "verified", False):
                    continue
                if getattr(obj, "stable_in_cart", False):
                    self._pending_products[session_id] = _PendingProduct(
                        track_id=obj.track_id,
                        label=obj.label,
                        placed_time=now,
                    )
                    pending = self._pending_products[session_id]
                    # نقطة مرجعية للفاتورة: نراقب فقط ما يُضاف بعد هذه اللحظة
                    receipt_monitor.checkpoint(session_id)
                    log.info(colorize(
                        f"[CV] Session {session_id}: product '{obj.label}' "
                        f"(track #{obj.track_id}) settled in cart — awaiting scan",
                        CYAN,
                    ))
                    break

        if pending is None:
            return alerts

        tracked_obj = tracked.get(pending.track_id)
        if tracked_obj is None or tracked_obj.label != pending.label:
            self._clear_pending_product(session_id)
            return alerts

        # ── الفاتورة زادت؟ إذاً المنتج مُسِح بشكل صحيح ─────────────────────
        if receipt_monitor.has_new_scan(session_id):
            tracked_obj.verified = True
            self._clear_pending_product(session_id)
            log.info(f"[CV] Session {session_id}: receipt updated — pending product cleared")
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
            tracked_obj.verified = True  # لا تُعِد إطلاق نفس الإنذار لنفس الجسم

            alert = self._build_theft_alert(session_id, pending)
            self._dispatch_theft_alert(session_id, alert)
            self._dispatch_dashboard_alert(session_id, alert)
            self._dispatch_brake(session_id, alert)

            self._clear_pending_product(session_id)
            self._cooldown_until[session_id] = time.time() + cv_config.ALERT_COOLDOWN
            alerts.append(alert)

        return alerts

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

    def _clear_pending_product(self, session_id: int):
        self._pending_products.pop(session_id, None)

    @property
    def has_pending(self) -> bool:
        """Return True when at least one pending product exists for any session."""
        return len(self._pending_products) > 0


# ── Singleton ─────────────────────────────────────────────────────────────
theft_service = TheftDetectionService()