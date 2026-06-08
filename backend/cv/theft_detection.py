"""
cv/theft_detection.py
=====================
نظام كشف السرقة باستخدام YOLOv8 + OpenCV.
يعمل على اللابتوب (Backend Server) فقط.
Raspberry Pi يُرسل فريمات الكاميرا عبر WebSocket، والـ Backend يعالجها هنا.

المنطق:
  1. استقبال frame من Raspberry Pi.
  2. تشغيل YOLOv8 للكشف عن الأجسام (يد + منتج).
  3. تتبع حركة المنتج.
  4. إذا اكتُشف منتج بدون مسح → إرسال تنبيه.
"""
import cv2
import numpy as np
import logging
import time
from typing import Optional, Callable, Dict, Any
from core.config import settings

log = logging.getLogger("neoshop.cv")

# تحميل YOLO اختياري — لا يوقف التطبيق إذا لم يكن مثبتاً
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    log.info("[CV] YOLOv8 available")
except ImportError:
    YOLO_AVAILABLE = False
    log.warning("[CV] YOLOv8 not installed — theft detection disabled")


class TheftDetectionService:
    """
    خدمة كشف السرقة — Singleton يعمل في الخلفية.
    يستقبل frames من Raspberry Pi ويُحلّلها بـ YOLOv8.
    """

    def __init__(self):
        self._model: Optional[Any] = None
        self._running = False
        self._on_theft_detected: Optional[Callable] = None
        # تتبع المنتجات التي تم مسحها في كل جلسة
        self._scanned_products: Dict[int, set] = {}  # session_id → set of product_ids
        # عتبة الثقة
        self.confidence_threshold = 0.6
        # مؤقت لمنع تكرار التنبيهات
        self._last_alert_time: Dict[int, float] = {}
        self.ALERT_COOLDOWN = 5.0  # ثوانٍ بين التنبيهات

    def load_model(self):
        """تحميل نموذج YOLOv8 — يُستدعى مرة واحدة عند بدء التطبيق."""
        if not YOLO_AVAILABLE:
            return
        try:
            self._model = YOLO(settings.YOLO_MODEL_PATH)
            log.info(f"[CV] YOLOv8 model loaded: {settings.YOLO_MODEL_PATH}")
        except Exception as e:
            log.error(f"[CV] Failed to load YOLO model: {e}")

    def set_theft_callback(self, callback: Callable):
        """تسجيل callback يُستدعى عند اكتشاف سرقة."""
        self._on_theft_detected = callback

    def register_scanned_product(self, session_id: int, product_id: int):
        """تسجيل منتج تم مسحه بالباركود لهذه الجلسة."""
        if session_id not in self._scanned_products:
            self._scanned_products[session_id] = set()
        self._scanned_products[session_id].add(product_id)

    def clear_session(self, session_id: int):
        """مسح بيانات الجلسة عند انتهائها."""
        self._scanned_products.pop(session_id, None)
        self._last_alert_time.pop(session_id, None)

    async def analyze_frame(self, frame_bytes: bytes, session_id: int) -> Optional[dict]:
        """
        تحليل frame واحد من كاميرا Raspberry Pi.
        يُعيد تنبيه إذا اكتُشف سلوك مشبوه.
        """
        if not self._model or not YOLO_AVAILABLE:
            return None

        try:
            # تحويل bytes إلى numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return None

            # تشغيل YOLO
            results = self._model(frame, conf=self.confidence_threshold, verbose=False)

            detections = []
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    conf   = float(box.conf[0])
                    label  = result.names[cls_id]
                    detections.append({
                        "class":      label,
                        "confidence": round(conf, 3),
                        "box":        box.xyxy[0].tolist(),
                    })

            # تحليل السلوك
            alert = self._analyze_behavior(detections, session_id)
            return alert

        except Exception as e:
            log.error(f"[CV] Frame analysis error: {e}")
            return None

    def _analyze_behavior(self, detections: list, session_id: int) -> Optional[dict]:
        """
        تحليل الكائنات المكتشفة للبحث عن سلوك مشبوه.
        منطق مبسّط: إذا كان هناك منتج في يد الشخص دون مسحه.
        """
        # منع التنبيهات المتكررة
        now = time.time()
        last_alert = self._last_alert_time.get(session_id, 0)
        if now - last_alert < self.ALERT_COOLDOWN:
            return None

        has_hand    = any(d["class"] in ("hand", "person") for d in detections)
        has_product = any(d["class"] in ("bottle", "cup", "book", "cell phone",
                                          "laptop", "mouse", "remote") for d in detections)

        if has_hand and has_product:
            # في النظام الحقيقي: تحقق من أن المنتج لم يُسحب
            # هنا نُعيد تنبيه بثقة متوسطة للعرض
            confidence = max(
                (d["confidence"] for d in detections if d["class"] in ("hand", "person")),
                default=0.5
            )

            if confidence > 0.7:
                self._last_alert_time[session_id] = now
                return {
                    "alert_type":       "UNSCANNED_ITEM",
                    "confidence_score": confidence,
                    "description":      "Possible unscanned item detected near hand",
                    "detections_count": len(detections),
                }

        return None

    @property
    def is_ready(self) -> bool:
        return self._model is not None


# ─── Singleton Instance ───────────────────────────────────────────────────────
theft_service = TheftDetectionService()
