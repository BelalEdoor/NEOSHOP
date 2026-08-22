"""
cv/tracker.py
=============

Simple object tracker for the graduation project.

Responsibilities
----------------
- Assign a stable track_id to each detected product.
- Match detections between frames using IoU.
- Detect basket entry/exit events.
- Keep object state only.

This tracker DOES NOT make theft decisions.
It only provides events for theft_logic.py.
"""

import time
from typing import Dict, List, Optional

from cv import config as cv_config
from cv import zones


def _iou(box_a, box_b):
    """Intersection over Union."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])

    inter = max(0.0, xb - xa) * max(0.0, yb - ya)

    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

    union = area_a + area_b - inter

    if union <= 0:
        return 0.0

    return inter / union


class TrackedObject:
    """Represents one tracked product."""

    _id_counter = 0

    def __init__(self, xyxy, label: str, frame_height: int, conf: float = 0.0):
        TrackedObject._id_counter += 1

        self.track_id = TrackedObject._id_counter

        self.label = label
        self.box = xyxy
        # ثقة آخر اكتشاف YOLO مطابَق لهذا الكائن — تُستخدَم بلوق لحظة
        # العبور A→B (راجع theft_logic.py) لطباعة "النوع + الدقّة" مباشرة
        # بنفس السطر، بدل الاعتماد على سطر PRODUCT DETECTED منفصل.
        self.conf = conf
        self.last_seen = time.time()

        # Basket state
        self.in_cart_zone = False
        self.previous_in_cart_zone = False

        # Cart-state events
        self.entered_cart = False
        self.left_cart = False
        self.stable_in_cart = False
        self.placed_in_cart = False
        self._cart_entry_time: Optional[float] = None

        # Used later by theft logic
        self.verified = False
        self.warning_started = None
        self.alarm_sent = False
        # True فقط بالإطار الذي أُنشئ فيه هذا الـ track لأول مرة (قبل أي
        # استدعاء لاحق لـ .update()). يُستخدَم لاكتشاف حالة "الغرض فقد
        # تتبّعه وهو بالسلة، وأُعيد اكتشافه بـ track_id جديد بمنطقة المسح"
        # — راجع theft_logic.py::_evaluate_pending_return_session.
        self.just_created = True

        # ── ⚠️ ذاكرة دائمة لكل منطقة (وليست لحظية) ─────────────────────────
        # بعكس entered_cart/left_cart (لحظيّان — يصيران True فقط بالإطار
        # الذي يحدث فيه العبور بالضبط، فيُفوَّتان لو لم يُحلَّل ذلك الإطار
        # تحديداً بسبب تخطّي الإطارات ANALYZE_EVERY_N_FRAMES)، هذان الحقلان
        # "يتذكّران" هل شُوهد هذا الجسم بكل منطقة *بأي وقت سابق على الإطلاق*
        # طوال عمر هذا الـ track — بغضّ النظر عن كون الفريم الذي شهد ذلك
        # حُلِّل بالضبط لحظة العبور أم لا. هذا يجعل القرار متيناً تماماً
        # أمام تخطّي الإطارات دون الحاجة لتحليل كل فريم على حساب الأداء.
        self.ever_seen_in_a = False
        self.ever_seen_in_b = False
        # علامتا "تمّ فحصه مرة واحدة" — تمنعان إعادة فتح نفس الفحص (دخول
        # أو إرجاع) لنفس الـ track أكثر من مرة.
        self.checked_entry = False
        self.checked_return = False

        self._update_zone(frame_height)

    def _update_zone(self, frame_height: int):

        _, cy = zones.bbox_center(self.box)

        zone = zones.classify_point(cy, frame_height)

        self.previous_in_cart_zone = self.in_cart_zone

        self.in_cart_zone = (zone == "cart")

        # تحديث الذاكرة الدائمة — مرة تصير True تبقى True لبقية عمر الـ track
        if self.in_cart_zone:
            self.ever_seen_in_b = True
        else:
            self.ever_seen_in_a = True

        self.entered_cart = (
            not self.previous_in_cart_zone
            and self.in_cart_zone
        )

        self.left_cart = (
            self.previous_in_cart_zone
            and not self.in_cart_zone
        )

        now = time.time()

        if self.entered_cart:
            self._cart_entry_time = now
            self.stable_in_cart = False
            self.placed_in_cart = False
        elif self.in_cart_zone and self._cart_entry_time is not None:
            is_stable = (now - self._cart_entry_time) >= cv_config.CART_STABILITY_SECONDS
            self.stable_in_cart = is_stable
            self.placed_in_cart = is_stable
        else:
            self._cart_entry_time = None
            self.stable_in_cart = False
            self.placed_in_cart = False

    def update(self, xyxy, frame_height: int, conf: float = None, label: str = None):

        self.just_created = False  # هذا استدعاء لاحق، مو إنشاء جديد

        self.box = xyxy
        if conf is not None:
            self.conf = conf
        if label is not None:
            # شبكة أمان إضافية: حتى لو حدثت مطابقة خاطئة يوماً بمكان آخر
            # بالكود، لا يبقى الـ track حاملاً تسمية قديمة خاطئة أبداً.
            self.label = label
        self.last_seen = time.time()

        self._update_zone(frame_height)


class Tracker:

    def __init__(self):

        # session_id -> {track_id : TrackedObject}
        self._tracked: Dict[int, Dict[int, TrackedObject]] = {}

    def update(
        self,
        session_id: int,
        detections: List[dict],
        frame_height: int,
    ) -> Dict[int, TrackedObject]:

        tracked = self._tracked.setdefault(session_id, {})

        now = time.time()

        # Remove disappeared objects
        stale = [
            tid
            for tid, obj in tracked.items()
            if now - obj.last_seen > 2.0
        ]

        for tid in stale:
            del tracked[tid]

        product_detections = [
            d
            for d in detections
            if d.get("category") == "product"
        ]

        matched_tracks = set()

        for det in product_detections:

            best_iou = cv_config.IOU_MATCH_THRESHOLD
            best_track = None

            for tid, obj in tracked.items():

                if tid in matched_tracks:
                    continue

                # ⚠️ باگ جوهري كان هنا: المطابقة كانت تعتمد على IoU فقط
                # (التداخل المكاني)، بدون أي شرط تطابق النوع (label). لو
                # اكتشاف جديد من فئة مختلفة تماماً (مثلاً "chips") ظهر
                # بمكان قريب من صندوق قديم متتبَّع من فئة أخرى (مثلاً
                # "bottle" غادر للتوّ أو تراكب معه)، كان يُطابَق معه غلط
                # ويرث الـ track القديم اسمه/حالته بالكامل — فتظهر تسمية
                # خاطئة باللوق والتنبيهات (رأينا "chips" بثقة 0.93 يُطبع
                # وبعدها "bottle" لنفس الاكتشاف بالضبط). لازم يتطابق النوع
                # أولاً، ثم IoU بينهم فقط.
                if obj.label != det["label"]:
                    continue

                score = _iou(det["xyxy"], obj.box)

                if score > best_iou:
                    best_iou = score
                    best_track = tid

            if best_track is None:

                obj = TrackedObject(
                    det["xyxy"],
                    det["label"],
                    frame_height,
                    conf=det.get("conf", 0.0),
                )

                tracked[obj.track_id] = obj
                matched_tracks.add(obj.track_id)

            else:

                tracked[best_track].update(
                    det["xyxy"],
                    frame_height,
                    conf=det.get("conf"),
                    label=det["label"],
                )

                matched_tracks.add(best_track)

        return tracked

    def get_tracked(self, session_id: int):

        return self._tracked.get(session_id, {})

    def clear_session(self, session_id: int):

        self._tracked.pop(session_id, None)