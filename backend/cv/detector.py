"""
cv/detector.py
==============
غلاف YOLOv8 + MediaPipe Hands. يطبَّع الاكتشافات إلى شكل موحّد:

    {"xyxy": (x1,y1,x2,y2), "conf": float, "label": raw_class_name,
     "category": "hand" | "product" | None}

`label` يبقى اسم الفئة الحقيقي كما يُخرجه النموذج المحمَّل (مثال: "coca_cola")
حتى تبقى رسائل التنبيه مفيدة ("Product (coca_cola) detected...") بدل
تعميمها لكلمة "product" فقط. الاسم يأتي من `result.names` مباشرة، فيعمل
تلقائياً مع أي نموذج (COCO أو مخصَّص) طالما أسماء فئاته موجودة ضمن
config.PRODUCT_CLASSES/HAND_CLASSES.
`category` هو المشتق من config.PRODUCT_CLASSES / HAND_CLASSES ويُستخدم من
قبل tracker.py / theft_logic.py لتحديد ما إذا كان الكائن يستحق التتبّع.

اليد: لا تُستنتَج بعد الآن من فئة COCO "person" (بديل خام يطابق أي إنسان في
الإطار، وليس اليد تحديداً). بدلاً من ذلك يُشغَّل MediaPipe Hands على نفس
الإطار وتُطبَّع نتائجه لنفس الشكل أعلاه، فلا يحتاج tracker.py/theft_logic.py
لأي تغيير في الواجهة. أي فئة "hand" حرفية من نموذج YOLO مخصَّص مستقبلاً
تُتجاهَل هنا لتفادي ازدواجية صناديق اليد — MediaPipe هو المصدر الوحيد لليد.

عند توفر نموذج مخصّص (product مدرَّب) لاحقاً: عدّل core.config.settings
.YOLO_MODEL_PATH فقط — هذا الملف يبقى كما هو، فقط تأكد أن أسماء الفئات في
النموذج الجديد موجودة ضمن PRODUCT_CLASSES أو حدّثها.
"""
import logging
from typing import List, Optional

# ── ⚠️ حماية من باگ بمكتبة platform القياسية (بايثون 3.10 على ماك،
# خصوصاً Apple Silicon): platform._Processor.get() — الدالة الداخلية
# يلي يعتمد عليها *كل* من platform.processor() و platform.uname()
# لجلب اسم المعالج عبر sysctl/uname بالـ subprocess — ممكن ترجع None
# بدل نص بهاي البيئة، فتنهار داخلياً بـ .strip(). هاد بينكسر
# ultralytics.get_cpu_info() (يستورد py-cpuinfo، ويلي بدوره يستدعي
# platform.uname() *وقت تعريف الكلاس نفسه* — يعني بايثون ما بتكاش
# الاستيراد الفاشل، فبيتكرر الخطأ على كل استدعاء YOLO/كل فريم كاميرا).
# ترقيع _Processor.get() هون (المصدر المشترك للطريقتين) بيغطي الحالتين
# معاً، بغض النظر عن أي مسار استدعاهم.
import platform as _platform

if hasattr(_platform, "_Processor"):
    _orig_processor_get = _platform._Processor.get

    def _safe_processor_get():
        try:
            return _orig_processor_get() or ""
        except Exception:
            return ""

    _platform._Processor.get = staticmethod(_safe_processor_get)

from core.config import settings
from cv import config as cv_config

log = logging.getLogger("neoshop.cv")

from cv.log_colors import colorize, CYAN, MAGENTA

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    log.warning("[CV] ultralytics not installed — theft detection disabled")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log.warning("[CV] opencv-python not installed — hand detection disabled")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    log.warning("[CV] mediapipe not installed — real hand detection disabled")


class Detector:
    def __init__(self):
        if not YOLO_AVAILABLE:
            raise RuntimeError("ultralytics is not installed")
        self.model = YOLO(settings.YOLO_MODEL_PATH)
        log.info(f"[CV] YOLOv8 model loaded: {settings.YOLO_MODEL_PATH} | classes: {self.model.names}")

        self._hands = None
        if MEDIAPIPE_AVAILABLE and CV2_AVAILABLE:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                model_complexity=cv_config.MEDIAPIPE_MODEL_COMPLEXITY,
                max_num_hands=cv_config.MAX_HANDS,
                min_detection_confidence=cv_config.HAND_DETECTION_CONFIDENCE,
                min_tracking_confidence=cv_config.HAND_TRACKING_CONFIDENCE,
            )
            log.info(f"[CV] MediaPipe Hands loaded (model_complexity={cv_config.MEDIAPIPE_MODEL_COMPLEXITY})")
        else:
            log.warning("[CV] MediaPipe Hands unavailable — no hand detections will be produced")

    def _categorize(self, raw_name: str) -> Optional[str]:
        normalized_name = raw_name.lower()

        if normalized_name in {name.lower() for name in cv_config.PRODUCT_CLASSES}:
            return "product"
        if normalized_name in {name.lower() for name in cv_config.HAND_CLASSES}:
            return "hand"
        return None

    def detect(self, frame, run_products: bool = True, run_hands: bool = True) -> List[dict]:
        """
        run_products=False يتخطّى YOLO، run_hands=False يتخطّى MediaPipe —
        يستخدمهما theft_logic.py حسب cv_config.ANALYZE_EVERY_N_FRAMES /
        HAND_ANALYZE_EVERY_N_FRAMES. اليد غير مستخدَمة في قرار السرقة، فتشغيلها
        أندر آمن تماماً وموفِّر ملحوظ لأن MediaPipe غالباً أثقل من نموذج YOLO
        المخصَّص الصغير هنا.
        """
        detections = self._detect_products(frame) if run_products else []
        if run_hands:
            detections.extend(self._detect_hands(frame))
        return detections

    def _detect_products(self, frame) -> List[dict]:
        results = self.model.predict(
            source=frame,
            imgsz=cv_config.YOLO_IMGSZ,
            conf=cv_config.CONFIDENCE_THRESHOLD,
            iou=0.45,
            max_det=cv_config.YOLO_MAX_DETECTIONS,
            verbose=False,
        )

        detections = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = result.names[cls_id]
                category = self._categorize(label)
                if category != "product":
                    continue
                conf = float(box.conf[0])
                xyxy = tuple(box.xyxy[0].tolist())
                x1, y1, x2, y2 = xyxy

                w = x2 - x1
                h = y2 - y1

                if w < 25 or h < 25:
                    continue

                detections.append({
                    "xyxy": xyxy,
                    "conf": round(conf, 3),
                    "label": label,
                    "category": category,
                })

        # ── لوق واضح ومميّز لكل منتج مكتشف — بالضبط الصيغة المطلوبة للتتبّع
        # السريع بالعين أثناء التطوير/التصحيح، ملوَّن حتى يبرز وسط بقية اللوق ──
        for d in detections:
            log.info(colorize(
                f"🎯 PRODUCT DETECTED — product: {d['label']} | accuracy: {d['conf']:.2f}",
                CYAN, bold=True,
            ))
        return detections

    def _detect_hands(self, frame) -> List[dict]:
        if not self._hands:
            return []

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)

        detections = []
        if results.multi_hand_landmarks:
            # كانت log.info — بمعدّل عدة إطارات بالثانية هاد I/O ملحوظ فعلياً.
            log.debug(colorize(
                f"✋ HAND DETECTED — count: {len(results.multi_hand_landmarks)}",
                MAGENTA,
            ))
            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                xs = [lm.x * w for lm in hand_landmarks.landmark]
                ys = [lm.y * h for lm in hand_landmarks.landmark]
                x1, x2 = max(0.0, min(xs)), min(float(w), max(xs))
                y1, y2 = max(0.0, min(ys)), min(float(h), max(ys))

                conf = 0.9
                if results.multi_handedness and i < len(results.multi_handedness):
                    conf = results.multi_handedness[i].classification[0].score

                detections.append({
                    "xyxy": (x1, y1, x2, y2),
                    "conf": round(float(conf), 3),
                    "label": "hand",
                    "category": "hand",
                })
        return detections