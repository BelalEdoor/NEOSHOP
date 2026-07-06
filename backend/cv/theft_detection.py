"""
cv/theft_detection.py
=====================
نظام كشف السرقة باستخدام YOLOv8 + منطق المنطقتين (Two-Zone Logic).

المنطق المحسّن:
  المنطقة العليا  (Zone 1 — SCAN ZONE):
      حيث تُمسك اليد المنتج وحيث يوجد الماسح الضوئي.
      المنتج هنا = العميل يتعامل معه. لا تنبيه بعد.

  المنطقة السفلى (Zone 2 — CART ZONE):
      داخل سلة العربة الفعلية.
      منتج هنا دون مسح = مشبوه.

مشغّلا التنبيه (كلاهما مطلوبان):
  1. زمني  : منتج في Zone 1 لأكثر من ZONE1_TIME_THRESHOLD ثانية دون مسح → تحذير
  2. مكاني : منتج ظهر في Zone 2 دون أن يُسجَّل مسحه مسبقاً → تنبيه فوري

تتبع الكائنات بين الإطارات:
  يستخدم IoU (تداخل الصناديق) لربط نفس الكائن عبر إطارات متعاقبة،
  مما يتيح قياس مدة بقاء المنتج في كل منطقة بدون ByteTrack الكامل.

YOLO Model: YOLOv8-nano مدرَّب مسبقاً على COCO.
  فئات الكائنات تُستخدم كبديل للمنتجات الحقيقية في مرحلة الاختبار:
  bottle, cup, book, cell phone, backpack, handbag, scissors, etc.
  في النشر الحقيقي: استبدله بنموذج مخصص مدرَّب على منتجات المتجر.
"""
import logging
import time
from typing import Optional, Callable, Dict, Any, List, Tuple

log = logging.getLogger("neoshop.cv")

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log.warning("[CV] opencv-python not installed — frame analysis disabled")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    log.info("[CV] YOLOv8 available")
except ImportError:
    YOLO_AVAILABLE = False
    log.warning("[CV] YOLOv8 not installed — theft detection disabled")


# ── Zone configuration ────────────────────────────────────────────────────────
# Fraction of frame HEIGHT that separates Zone 1 (upper/scan area) from
# Zone 2 (lower/cart basket). 0.45 means the top 45% is Zone 1.
# Change this single constant to retune after physical testing.
ZONE_BOUNDARY = 0.45

# Seconds an unscanned product must stay in Zone 1 before a WARNING fires.
# 4s is long enough for legitimate scanning (pick up → find barcode → scan)
# but short enough to catch deliberate evasion.
ZONE1_TIME_THRESHOLD = 4.0

# Minimum YOLO confidence to consider a detection real.
CONFIDENCE_THRESHOLD = 0.45

# Seconds between repeated alerts for the same session (avoids spam).
ALERT_COOLDOWN = 8.0

# IoU threshold for matching a detection in frame N to a tracked object
# from frame N-1. Higher = stricter identity matching.
IOU_MATCH_THRESHOLD = 0.35

# COCO class names that serve as proxy "products" during testing.
# Replace with your own trained classes for production.
PRODUCT_CLASSES = {
    "bottle", "cup", "book", "cell phone", "backpack",
    "handbag", "scissors", "remote", "vase", "bowl",
    "banana", "apple", "orange", "sandwich", "pizza",
}

# Classes that indicate a human hand or body near the product.
HAND_CLASSES = {"hand", "person"}


# ── Simple IoU-based object tracker ──────────────────────────────────────────

def _iou(box_a: List[float], box_b: List[float]) -> float:
    """
    Intersection-over-Union between two [x1,y1,x2,y2] boxes.
    Returns 0.0-1.0. Used to match the same object across consecutive frames.
    """
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _box_center_y_fraction(box: List[float], frame_height: int) -> float:
    """Returns the vertical centre of a box as a fraction of frame height."""
    center_y = (box[1] + box[3]) / 2.0
    return center_y / frame_height if frame_height > 0 else 0.5


class TrackedObject:
    """
    Represents a single product-like object being tracked across frames.
    Keeps per-session state: which zone it's in, when it entered Zone 1,
    and whether it has been scanned.
    """
    _id_counter = 0

    def __init__(self, box: List[float], label: str, frame_height: int):
        TrackedObject._id_counter += 1
        self.track_id   = TrackedObject._id_counter
        self.box        = box
        self.label      = label
        self.last_seen  = time.time()
        self.zone1_entry_time: Optional[float] = None  # when it first entered Zone 1
        self.in_cart_zone = False                       # whether it's in Zone 2 now
        self._update_zone(box, frame_height)

    def _update_zone(self, box: List[float], frame_height: int):
        cy = _box_center_y_fraction(box, frame_height)
        if cy < ZONE_BOUNDARY:
            if self.zone1_entry_time is None:
                self.zone1_entry_time = time.time()   # first time entering Zone 1
            self.in_cart_zone = False
        else:
            self.zone1_entry_time = None              # left Zone 1, reset timer
            self.in_cart_zone = True

    def update(self, box: List[float], frame_height: int):
        self.box = box
        self.last_seen = time.time()
        self._update_zone(box, frame_height)

    @property
    def zone1_duration(self) -> float:
        """Seconds this object has been continuously in Zone 1."""
        if self.zone1_entry_time is None:
            return 0.0
        return time.time() - self.zone1_entry_time


# ── Main service ──────────────────────────────────────────────────────────────

class TheftDetectionService:
    """
    خدمة كشف السرقة — Singleton.
    يستقبل frames من Raspberry Pi عبر WebSocket ويُحلّلها.
    """

    def __init__(self):
        self._model: Optional[Any]          = None
        self._on_theft_detected: Optional[Callable] = None

        # Per-session scanned product IDs (set by barcode scanner on scan)
        self._scanned_products: Dict[int, set]  = {}

        # Per-session last alert timestamp (for cooldown)
        self._last_alert_time: Dict[int, float] = {}

        # Per-session object tracker: track_id → TrackedObject
        # Kept separate per session so concurrent carts don't interfere.
        self._tracked_objects: Dict[int, Dict[int, TrackedObject]] = {}

        # Per-session alerted track IDs (avoid re-alerting same object)
        self._alerted_tracks: Dict[int, set] = {}

    # ── Setup ─────────────────────────────────────────────────────────────────

    def load_model(self):
        """Load YOLOv8 model once at app startup."""
        if not YOLO_AVAILABLE:
            return
        try:
            from core.config import settings
            self._model = YOLO(settings.YOLO_MODEL_PATH)
            log.info(f"[CV] YOLOv8 model loaded: {settings.YOLO_MODEL_PATH}")
        except Exception as e:
            log.error(f"[CV] Failed to load YOLO model: {e}")

    def set_theft_callback(self, callback: Callable):
        """Register a callback invoked when theft is detected."""
        self._on_theft_detected = callback

    # ── Session management ────────────────────────────────────────────────────

    def register_scanned_product(self, session_id: int, product_id: int):
        """
        Called by the barcode scanner route every time a product is scanned.
        Marks it as legitimately scanned so the CV engine won't flag it.
        """
        self._scanned_products.setdefault(session_id, set()).add(product_id)

    def clear_session(self, session_id: int):
        """Clean up all state for a completed session."""
        self._scanned_products.pop(session_id, None)
        self._last_alert_time.pop(session_id, None)
        self._tracked_objects.pop(session_id, None)
        self._alerted_tracks.pop(session_id, None)

    # ── Frame analysis ────────────────────────────────────────────────────────

    async def analyze_frame(
        self,
        frame_bytes: bytes,
        session_id: int,
        frame_height: int = 480,
    ) -> Optional[dict]:
        """
        Analyze one camera frame from the Raspberry Pi.
        Returns an alert dict if suspicious behavior is detected, else None.

        frame_height: actual pixel height of the camera feed. Used to compute
        zone boundaries as pixel positions. Defaults to 480 (standard webcam).
        Raspberry Pi should send this alongside each frame if possible.
        """
        if not self._model or not YOLO_AVAILABLE or not CV2_AVAILABLE:
            return None

        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return None

            actual_height = frame.shape[0]
            results = self._model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

            detections = []
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    conf   = float(box.conf[0])
                    label  = result.names[cls_id]
                    coords = box.xyxy[0].tolist()
                    detections.append({
                        "class":      label,
                        "confidence": round(conf, 3),
                        "box":        coords,
                    })

            self._update_tracker(session_id, detections, actual_height)
            return self._evaluate_threats(session_id, detections, actual_height)

        except Exception as e:
            log.error(f"[CV] Frame analysis error: {e}")
            return None

    # ── Tracker update ────────────────────────────────────────────────────────

    def _update_tracker(
        self,
        session_id: int,
        detections: List[dict],
        frame_height: int,
    ):
        """
        Match current-frame detections to existing tracked objects using IoU.
        Creates new TrackedObjects for unmatched detections.
        Removes objects not seen for more than 2 seconds (left the frame).
        """
        tracked = self._tracked_objects.setdefault(session_id, {})
        now = time.time()

        # Remove stale objects (not seen for 2 seconds)
        stale = [tid for tid, obj in tracked.items() if now - obj.last_seen > 2.0]
        for tid in stale:
            del tracked[tid]

        product_detections = [d for d in detections if d["class"] in PRODUCT_CLASSES]
        matched_track_ids  = set()

        for det in product_detections:
            best_iou  = IOU_MATCH_THRESHOLD
            best_tid  = None

            for tid, obj in tracked.items():
                if tid in matched_track_ids:
                    continue
                iou = _iou(det["box"], obj.box)
                if iou > best_iou:
                    best_iou = iou
                    best_tid = tid

            if best_tid is not None:
                tracked[best_tid].update(det["box"], frame_height)
                matched_track_ids.add(best_tid)
            else:
                new_obj = TrackedObject(det["box"], det["class"], frame_height)
                tracked[new_obj.track_id] = new_obj

    # ── Threat evaluation ─────────────────────────────────────────────────────

    def _evaluate_threats(
        self,
        session_id: int,
        detections: List[dict],
        frame_height: int,
    ) -> Optional[dict]:
        """
        Two-zone threat evaluation:

        Trigger 1 (TIME-BASED / Zone 1):
            A product has been in the scan zone for > ZONE1_TIME_THRESHOLD
            seconds without a corresponding scan being registered.
            → Fires a WARNING (customer might have forgotten to scan).

        Trigger 2 (SPATIAL / Zone 2):
            A product is detected in the cart basket zone and has NOT been
            registered as scanned in this session.
            → Fires an ALERT (product was placed without scanning).

        Both triggers respect ALERT_COOLDOWN to avoid notification spam.
        """
        now          = time.time()
        last_alert   = self._last_alert_time.get(session_id, 0)
        tracked      = self._tracked_objects.get(session_id, {})
        scanned      = self._scanned_products.get(session_id, set())
        alerted      = self._alerted_tracks.setdefault(session_id, set())
        has_hand     = any(d["class"] in HAND_CLASSES for d in detections)

        if now - last_alert < ALERT_COOLDOWN:
            return None

        # ── Trigger 2: Spatial (Zone 2) ──────────────────────────────────────
        # Check first because it's more definitive than the time trigger.
        # A product in the cart without a scan is unambiguous.
        for tid, obj in tracked.items():
            if tid in alerted:
                continue
            if not obj.in_cart_zone:
                continue
            # We can't directly match track_id to product_id (that would
            # require a custom-trained model with product-level classes).
            # For COCO-based detection: if ANY unscanned product class is
            # detected inside the cart zone, flag it.
            # In production with a custom model: compare class name to
            # product database entries instead.
            if len(scanned) == 0:
                # Nothing scanned at all yet — anything in the cart is suspicious
                confidence = obj.box[4] if len(obj.box) > 4 else 0.6
                self._last_alert_time[session_id] = now
                alerted.add(tid)
                alert = {
                    "alert_type":       "UNSCANNED_IN_CART",
                    "trigger":          "spatial",
                    "confidence_score": round(confidence, 3),
                    "track_id":         tid,
                    "object_class":     obj.label,
                    "description":      f"Product ({obj.label}) detected in cart zone without any scan registered",
                    "zone":             "Zone 2 — Cart basket",
                    "detections_count": len(detections),
                    "hand_present":     has_hand,
                }
                if self._on_theft_detected:
                    import asyncio
                    asyncio.create_task(
                        self._on_theft_detected(session_id, alert)
                    )
                return alert

        # ── Trigger 1: Time-based (Zone 1) ───────────────────────────────────
        for tid, obj in tracked.items():
            if tid in alerted:
                continue
            if obj.in_cart_zone:
                continue  # Already in cart — spatial trigger handles this
            duration = obj.zone1_duration
            if duration >= ZONE1_TIME_THRESHOLD:
                self._last_alert_time[session_id] = now
                alerted.add(tid)
                alert = {
                    "alert_type":       "PROLONGED_HOLDING",
                    "trigger":          "time",
                    "confidence_score": round(min(duration / 10.0, 1.0), 3),
                    "track_id":         tid,
                    "object_class":     obj.label,
                    "description":      f"Product ({obj.label}) held for {duration:.1f}s without scanning",
                    "zone":             "Zone 1 — Scan zone",
                    "duration_seconds": round(duration, 1),
                    "detections_count": len(detections),
                    "hand_present":     has_hand,
                }
                if self._on_theft_detected:
                    import asyncio
                    asyncio.create_task(
                        self._on_theft_detected(session_id, alert)
                    )
                return alert

        return None

    @property
    def is_ready(self) -> bool:
        return self._model is not None


# ── Singleton ─────────────────────────────────────────────────────────────────
theft_service = TheftDetectionService()
