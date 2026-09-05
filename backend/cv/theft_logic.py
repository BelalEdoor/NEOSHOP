"""
cv/theft_logic.py
=================
Production-style theft monitoring flow for the graduation project.
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
    track_id: int
    label: str
    placed_time: float
    state: _PendingState = _PendingState.WAITING
    warning_started: Optional[float] = None
    warning_dispatched: bool = False
    alarm_sent: bool = False


@dataclass
class _PendingReturn:
    track_id: int
    label: str
    left_time: float
    warning_dispatched: bool = False


class TheftDetectionService:
    def __init__(self):
        self._detector: Optional[Any] = None
        self._on_theft_detected: Optional[Callable] = None
        self._on_dashboard_alert: Optional[Callable] = None
        self._on_brake_callback: Optional[Callable] = None
        self._on_cleared_callback: Optional[Callable] = None
        self.tracker = Tracker()

        self._pending_products: Dict[int, _PendingProduct] = {}
        self._pending_returns: Dict[int, _PendingReturn] = {}
        self._cooldown_until: Dict[int, float] = {}
        self._frame_counters: Dict[int, int] = {}
        self._recently_verified: Dict[int, Dict[str, float]] = {}
        self._obstruction_since: Dict[int, Optional[float]] = {}
        self._obstruction_cooldown_until: Dict[int, float] = {}
        self._obstruction_last_debug: Dict[int, float] = {}
        self._in_cart_count: Dict[int, Counter] = {}
        # key (مثال: "no_theft_cb", "preview_fail:3") -> آخر وقت طُبعت فيه
        # هذه الرسالة. تُستخدَم فقط لمنع تكرار رسائل التحذير/الخطأ نفسها
        # كل فريم (راجع _throttled_log). لا تؤثر على القرارات، لوق فقط.
        self._last_log_at: Dict[str, float] = {}

    def load_model(self):
        from cv.detector import Detector
        try:
            self._detector = Detector()
        except Exception as exc:
            log.error(f"[CV] Failed to load YOLO model: {exc}")

    def set_theft_callback(self, callback: Callable):
        self._on_theft_detected = callback

    def set_dashboard_callback(self, callback: Callable):
        self._on_dashboard_alert = callback

    def set_brake_callback(self, callback: Callable):
        self._on_brake_callback = callback

    def set_cleared_callback(self, callback: Callable):
        self._on_cleared_callback = callback

    @property
    def is_ready(self) -> bool:
        return self._detector is not None

    # ── Logging helpers ──────────────────────────────────────────────────
    def _throttled_log(self, key: str, level: int, message: str, interval: float = None):
        """
        يطبع نفس الرسالة (بنفس المفتاح `key`) أول مرة فوراً، وبعدها بحد
        أقصى مرة كل `interval` ثانية — بدل إغراق اللوق بنفس السطر مئات
        المرات لأن analyze_frame يستدعي هذه المسارات كل فريم (مثال:
        callback غير مسجَّل، أو فشل نشر المعاينة). لا تُستخدَم لرسائل
        الأحداث المهمة (عبور/تحذير/فرامل) التي أصلاً لا تتكرر كل فريم.
        """
        interval = getattr(cv_config, "LOG_THROTTLE_SECONDS", 30.0) if interval is None else interval
        now = time.time()
        if now - self._last_log_at.get(key, 0.0) < interval:
            return
        self._last_log_at[key] = now
        log.log(level, message)

    @staticmethod
    def _factors_str(obj) -> str:
        """
        يبني سطر واحد يلخّص *كل* العوامل المؤثّرة على قرار هذا الجسم
        المتتبَّع لحظة اتخاذه — يُلحَق بنهاية رسائل اللوق للحالات الفعلية
        (عبور/تحذير/فرامل) حتى يمكن معرفة "ليش صار هيك بالضبط" من اللوق
        وحده دون الحاجة لتشغيل مُصحِّح.
        """
        return (
            f"[factors: track=#{getattr(obj, 'track_id', '?')} "
            f"label={getattr(obj, 'label', '?')} "
            f"conf={getattr(obj, 'conf', 0.0):.2f} "
            f"in_cart_zone={getattr(obj, 'in_cart_zone', None)} "
            f"ever_seen_in_a={getattr(obj, 'ever_seen_in_a', None)} "
            f"ever_seen_in_b={getattr(obj, 'ever_seen_in_b', None)} "
            f"stable_in_cart={getattr(obj, 'stable_in_cart', None)} "
            f"checked_entry={getattr(obj, 'checked_entry', None)} "
            f"checked_return={getattr(obj, 'checked_return', None)} "
            f"verified={getattr(obj, 'verified', None)}]"
        )

    def register_scanned_product(self, session_id: int, product_id: int, product_label: str = None):
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
        if not label:
            return
        self._recently_verified.setdefault(session_id, {})[label.strip().lower()] = time.time()

    def _in_cart_incr(self, session_id: int, label: str, delta: int = 1):
        if not label:
            return
        counter = self._in_cart_count.setdefault(session_id, Counter())
        key = label.strip().lower()
        counter[key] = max(0, counter[key] + delta)
        if counter[key] == 0:
            del counter[key]

    def _in_cart_has(self, session_id: int, label: str) -> bool:
        counter = self._in_cart_count.get(session_id)
        if not counter or not label:
            return False
        needle = label.strip().lower()
        return any(_labels_match(needle, k) and v > 0 for k, v in counter.items())

    def _in_cart_consume_one(self, session_id: int, label: str) -> bool:
        counter = self._in_cart_count.get(session_id)
        if not counter or not label:
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
        if not table or not label:
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
        self._mark_tracked_verified(session_id)
        self._clear_pending_product(session_id)
        self._pending_returns.pop(session_id, None)
        self._cooldown_until[session_id] = time.time() + cv_config.ALERT_COOLDOWN

    def clear_session(self, session_id: int):
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
        from cv.receipt_monitor import _labels_match
        for obj in self.tracker.get_tracked(session_id).values():
            if matching_label is None or _labels_match(matching_label, obj.label):
                obj.verified = True

    async def analyze_frame(
        self,
        frame_bytes: bytes,
        session_id: int,
        frame_height: int = 480,
    ) -> List[dict]:
        if not self._detector or not CV2_AVAILABLE:
            return []

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

            self._check_camera_obstruction(session_id, frame)

            if run_products:
                detections = self._detector.detect(frame, run_products=True, run_hands=run_hands)
                alerts = self.update(session_id, detections, frame.shape[0])
            else:
                detections = self._detector.detect(frame, run_products=False, run_hands=True)
                alerts = []

            self._publish_preview(session_id, frame, detections)
            return alerts
        except Exception as exc:
            log.error(f"[CV] Frame analysis error: {exc}", exc_info=True)
            return []

    def _check_camera_obstruction(self, session_id: int, frame) -> None:
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            std = float(gray.std())
        except Exception:
            return

        now = time.time()

        if std >= cv_config.CAMERA_OBSTRUCTION_STD_THRESHOLD:
            self._obstruction_since.pop(session_id, None)
            return

        if now < self._obstruction_cooldown_until.get(session_id, 0.0):
            return

        since = self._obstruction_since.get(session_id)
        if since is None:
            self._obstruction_since[session_id] = now
            return

        if now - since < cv_config.CAMERA_OBSTRUCTION_SECONDS:
            return

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
        try:
            from cv.preview import preview_store, annotate_and_encode
            tracked = self.tracker.get_tracked(session_id)
            pending = self._pending_products.get(session_id)
            jpeg = annotate_and_encode(frame, detections, tracked, pending)
            if jpeg:
                preview_store.publish(session_id, jpeg)
        except Exception as exc:
            self._throttled_log(
                f"preview_fail:{session_id}", logging.WARNING,
                f"[CV] preview publish failed (session {session_id}): {exc}",
            )

    def update(self, session_id: int, detections: List[dict], frame_height: int) -> List[dict]:
        self.tracker.update(session_id, detections, frame_height)
        alerts = self._evaluate_pending_session(session_id)
        alerts += self._evaluate_pending_return_session(session_id)
        return alerts

    def _open_entry_check(self, session_id: int, obj, now: float):
        if self._was_recently_verified(session_id, obj.label):
            obj.verified = True
            log.debug(colorize(
                f"[CV] Session {session_id}: 🔁 '{obj.label}' re-detected "
                f"(track #{obj.track_id}) — already verified recently, ignoring "
                f"{self._factors_str(obj)}",
                CYAN,
            ))
            return None

        log.info(colorize(
            f"[CV] Session {session_id}: 🚶 CROSSED A→B — product: {obj.label} "
            f"{self._factors_str(obj)}",
            CYAN, bold=True,
        ))
        log.debug(colorize(
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

    def _evaluate_pending_session(self, session_id: int) -> List[dict]:
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        pending = self._pending_products.get(session_id)
        alerts: List[dict] = []

        if pending is None:
            if now < self._cooldown_until.get(session_id, 0.0):
                return alerts

            for obj in tracked.values():
                if getattr(obj, "verified", False):
                    continue
                if getattr(obj, "checked_entry", False):
                    continue
                if not getattr(obj, "in_cart_zone", False):
                    continue

                seen_in_a = getattr(obj, "ever_seen_in_a", False)
                settled = getattr(obj, "stable_in_cart", False)

                if not seen_in_a and not settled:
                    continue

                if self._was_recently_verified(session_id, obj.label):
                    obj.verified = True
                    obj.checked_entry = True
                    log.debug(colorize(
                        f"[CV] Session {session_id}: 🔁 '{obj.label}' re-detected "
                        f"(track #{obj.track_id}) — already verified recently, ignoring "
                        f"{self._factors_str(obj)}",
                        CYAN,
                    ))
                    continue

                if not seen_in_a:
                    log.info(colorize(
                        f"[CV] Session {session_id}: 🕵️ '{obj.label}' (track #{obj.track_id}) "
                        f"settled in Zone B without ever being seen in Zone A — "
                        f"treating as a theft candidate {self._factors_str(obj)}",
                        CYAN, bold=True,
                    ))

                obj.checked_entry = True
                result = self._open_entry_check(session_id, obj, now)
                if result is not None:
                    break

            return alerts

        if pending is None:
            return alerts

        tracked_obj = tracked.get(pending.track_id)

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

            pending.state = _PendingState.ALARM
            pending.alarm_sent = True
            if tracked_obj is not None:
                tracked_obj.verified = True
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

    def _evaluate_pending_return_session(self, session_id: int) -> List[dict]:
        now = time.time()
        tracked = self.tracker.get_tracked(session_id)
        pending = self._pending_returns.get(session_id)
        alerts: List[dict] = []

        if pending is None:
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
                            f"cancelling entry-check, switching to return-check {self._factors_str(obj)}",
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
                if getattr(obj, "checked_return", False):
                    continue
                if getattr(obj, "in_cart_zone", True):
                    continue
                if not getattr(obj, "ever_seen_in_b", False):
                    continue

                obj.checked_return = True

                entry_pending = self._pending_products.get(session_id)
                if entry_pending is not None and entry_pending.track_id == obj.track_id:
                    log.info(colorize(
                        f"[CV] Session {session_id}: ↩️ '{obj.label}' (track #{obj.track_id}) "
                        f"passed through to Zone A before settling — cancelling entry-check, "
                        f"switching fully to return-check",
                        CYAN,
                    ))
                    if entry_pending.warning_dispatched:
                        self._dispatch_cleared(session_id)
                    self._clear_pending_product(session_id)

                log.info(colorize(
                    f"[CV] Session {session_id}: 🚶 CROSSED B→A (returned) — product: {obj.label} "
                    f"{self._factors_str(obj)}",
                    CYAN, bold=True,
                ))
                log.debug(colorize(
                    f"[CV] Session {session_id}: 🔍 Checking invoice for removal of '{obj.label}'...",
                    CYAN,
                ))

                self._in_cart_consume_one(session_id, obj.label)

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
            "grace_seconds": None,
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
            self._throttled_log(
                "no_theft_cb", logging.WARNING,
                "[CV] No theft callback registered; skipping theft alert dispatch",
            )

    def _dispatch_dashboard_alert(self, session_id: int, alert: dict):
        if self._on_dashboard_alert:
            self._schedule(self._on_dashboard_alert(session_id, alert))
        else:
            self._throttled_log(
                "no_dashboard_cb", logging.WARNING,
                "[CV] Dashboard alert callback not configured",
            )

    def _dispatch_cleared(self, session_id: int):
        if self._on_cleared_callback:
            self._schedule(self._on_cleared_callback(session_id))

    def _dispatch_brake(self, session_id: int, alert: dict):
        if self._on_brake_callback:
            self._schedule(self._on_brake_callback(session_id, alert))
        else:
            self._throttled_log(
                "no_brake_cb", logging.WARNING,
                "[CV] Brake callback not configured",
            )

    @staticmethod
    def _schedule(coro):
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            coro.close()
            log.debug("[CV] No running event loop — alert callback skipped (offline mode)")

    def _clear_pending_product(self, session_id: int, matching_label: str = None):
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
        return len(self._pending_products) > 0

    def has_pending_for(self, session_id: int) -> bool:
        return session_id in self._pending_products


theft_service = TheftDetectionService()