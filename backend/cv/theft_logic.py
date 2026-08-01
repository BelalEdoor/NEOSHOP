"""
cv/theft_logic.py
==================
طبقة القرار فوق الاكتشاف + التتبّع.

القاعدة، ببساطة:
  كائن "منتج" ظهر في Zone 1 (منطقة المسح) ثم استقرّ في Zone 2 (سلة العربة)
  لـ SETTLE_FRAMES_REQUIRED إطاراً متتالياً، يجب أن يكون هناك مسح مسجَّل
  خلال SCAN_MATCH_WINDOW_SECONDS قبل تلك اللحظة — وإلا: تنبيه (مرة واحدة ثم تهدئة).

مشغّلا التنبيه (مستقلّان، كلاهما من theft_detection.py الأصلي):
  1. زمني (Zone 1): منتج بلا مسح لأكثر من ZONE1_TIME_THRESHOLD ثانية → تحذير مبكر
     (PROLONGED_HOLDING).
  2. مكاني (Zone 2): منتج استقرّ في السلة بلا مسح حديث → تنبيه فوري
     (UNSCANNED_IN_CART). هذا يحل محل الفحص القديم `len(scanned) == 0` الذي
     كان يُعفي الجلسة بأكملها للأبد بعد أول مسح — الآن الفحص يعتمد على حداثة
     آخر مسح، وليس "هل حدث أي مسح على الإطلاق في هذه الجلسة".

شرط "الإفلات" (release) قبل أهلية UNSCANNED_IN_CART:
  لا يبدأ عدّاد الاستقرار (settle) في Zone 2 إلا لمنتج تتحقق فيه سلسلة
  الأحداث كاملة: التُقِط بيد أثناء وجوده في Zone 1 (tracker.py:picked_up)
  ثم انفصلت اليد عنه لاحقاً (tracker.py:released) — عادة أثناء استقراره في
  Zone 2. هذا يمنع تنبيهين كاذبين:
    - منتج ظهر مباشرة في Zone 2 دون أي علاقة سابقة بيد (مثال: هاتف على
      حافة السلة) — لم يُلتقط أصلاً فلا يبدأ العدّاد أبداً.
    - منتج ما زال ممسوكاً فعلياً بيد العميل داخل Zone 2 (لم يُفلَت بعد) —
      لا يُعتبر "مستقرّاً" حتى تنفصل اليد عنه.

كل تنبيه لكائن (track_id) واحد يُطلَق مرة واحدة فقط (ثم يُعتبر "منتهياً"،
سواء أُطلق تنبيه أو تبيّن أنه مسحوح شرعاً) — لا تُعاد معالجته.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from cv import config as cv_config
from cv import scan_events, zones
from cv.tracker import Tracker

log = logging.getLogger("neoshop.cv")

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log.warning("[CV] opencv-python not installed — frame analysis disabled")


@dataclass
class _TrackAlertState:
    zone2_streak: int = 0
    settled: bool = False
    alerted: bool = False


class TheftDetectionService:
    """خدمة كشف السرقة — Singleton. تستقبل detections لكل جلسة وتقرّر التنبيه."""

    def __init__(self):
        self._detector: Optional[Any] = None
        self._on_theft_detected: Optional[Callable] = None
        self.tracker = Tracker()

        # session_id -> last alert timestamp (للتهدئة)
        self._last_alert_time: Dict[int, float] = {}
        # session_id -> {track_id -> _TrackAlertState}
        self._alert_states: Dict[int, Dict[int, _TrackAlertState]] = {}

    # ── Setup ─────────────────────────────────────────────────────────────
    def load_model(self):
        """تحميل نموذج YOLOv8 مرة واحدة عند بدء التطبيق."""
        from cv.detector import Detector
        try:
            self._detector = Detector()
        except Exception as e:
            log.error(f"[CV] Failed to load YOLO model: {e}")

    def set_theft_callback(self, callback: Callable):
        """تسجيل دالة تُستدعى عند اكتشاف سرقة: callback(session_id, alert_dict)."""
        self._on_theft_detected = callback

    # ── Session management ───────────────────────────────────────────────
    def register_scanned_product(self, session_id: int, product_id: int):
        """يُستدعى من نقطة مسح الباركود الحقيقية عند كل عملية مسح ناجحة."""
        scan_events.register_scan_event(session_id, product_id)

    def clear_session(self, session_id: int):
        """تنظيف كل حالة الجلسة (تتبّع + مسح + تنبيهات) عند انتهاء التسوق."""
        self.tracker.clear_session(session_id)
        scan_events.clear_session(session_id)
        self._last_alert_time.pop(session_id, None)
        self._alert_states.pop(session_id, None)

    # ── Frame analysis (from a camera feed) ──────────────────────────────
    async def analyze_frame(
        self,
        frame_bytes: bytes,
        session_id: int,
        frame_height: int = 480,
    ) -> List[dict]:
        """يحلّل إطار كاميرا واحداً (JPEG bytes). يُرجع قائمة التنبيهات الجديدة."""
        if not self._detector or not CV2_AVAILABLE:
            return []

        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return []
            detections = self._detector.detect(frame)
            return self.update(session_id, detections, frame.shape[0])
        except Exception as e:
            log.error(f"[CV] Frame analysis error: {e}")
            return []

    # ── Direct pipeline entrypoint (frame already detected elsewhere) ────
    def update(self, session_id: int, detections: List[dict], frame_height: int) -> List[dict]:
        """
        detections: قائمة {"xyxy","conf","label","category"} (خرج Detector.detect).
        يحدّث المتتبّع ثم يقيّم التهديدات. يُرجع قائمة التنبيهات الجديدة لهذا الإطار.
        """
        self.tracker.update(session_id, detections, frame_height)
        return self._evaluate_threats(session_id, detections)

    # ── Threat evaluation ─────────────────────────────────────────────────
    def _evaluate_threats(self, session_id: int, detections: List[dict]) -> List[dict]:
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        states = self._alert_states.setdefault(session_id, {})
        has_hand = any(d.get("category") == "hand" for d in detections)
        last_alert = self._last_alert_time.get(session_id, 0)

        # تنظيف حالات التنبيه للكائنات التي لم تعد متتبَّعة
        for tid in list(states.keys()):
            if tid not in tracked:
                del states[tid]

        alerts: List[dict] = []

        for tid, obj in tracked.items():
            state = states.setdefault(tid, _TrackAlertState())
            if state.alerted:
                continue

            if not obj.in_cart_zone:
                # في Zone 1 — أعد ضبط عدّاد الاستقرار، وتحقّق من التحذير الزمني
                state.zone2_streak = 0
                duration = obj.zone1_duration
                if duration >= cv_config.ZONE1_TIME_THRESHOLD:
                    if now - last_alert < cv_config.ALERT_COOLDOWN:
                        continue
                    alert = {
                        "alert_type": "PROLONGED_HOLDING",
                        "trigger": "time",
                        "confidence_score": round(min(duration / 10.0, 1.0), 3),
                        "track_id": tid,
                        "object_class": obj.label,
                        "description": f"Product ({obj.label}) held for {duration:.1f}s without scanning",
                        "zone": "Zone 1 — Scan zone",
                        "duration_seconds": round(duration, 1),
                        "hand_present": has_hand,
                    }
                    state.alerted = True
                    last_alert = now
                    self._last_alert_time[session_id] = now
                    alerts.append(alert)
                    if self._on_theft_detected:
                        import asyncio
                        asyncio.create_task(self._on_theft_detected(session_id, alert))
                continue

            # في Zone 2 — لا يبدأ عدّاد الاستقرار إلا بعد "الإفلات" (التُقِط
            # بيد في Zone 1 ثم انفصلت عنه اليد). كائن لم يُلتقط قط، أو ما زال
            # ممسوكاً حالياً، لا يستحق تنبيهاً أبداً.
            if not obj.released:
                state.zone2_streak = 0
                continue

            # في Zone 2 وأُفلِت — عدّاد الاستقرار
            state.zone2_streak += 1
            if state.zone2_streak >= cv_config.SETTLE_FRAMES_REQUIRED:
                state.settled = True

            if not state.settled:
                continue

            if scan_events.has_recent_scan(session_id, cv_config.SCAN_MATCH_WINDOW_SECONDS):
                # مسحوح شرعاً — لا تنبيه لهذا الكائن أبداً
                state.alerted = True
                continue

            if now - last_alert < cv_config.ALERT_COOLDOWN:
                continue

            alert = {
                "alert_type": "UNSCANNED_IN_CART",
                "trigger": "spatial",
                "confidence_score": 0.75,
                "track_id": tid,
                "object_class": obj.label,
                "description": f"Product ({obj.label}) detected in cart zone without any scan registered",
                "zone": "Zone 2 — Cart basket",
                "hand_present": has_hand,
            }
            state.alerted = True
            last_alert = now
            self._last_alert_time[session_id] = now
            alerts.append(alert)
            if self._on_theft_detected:
                import asyncio
                asyncio.create_task(self._on_theft_detected(session_id, alert))

        return alerts

    @property
    def is_ready(self) -> bool:
        return self._detector is not None


# ── Singleton ─────────────────────────────────────────────────────────────
theft_service = TheftDetectionService()
