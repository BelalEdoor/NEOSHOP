"""
cv/tracker.py
=============
تتبّع الكائنات بين الإطارات باستخدام IoU (تداخل الصناديق) — يربط نفس المنتج
عبر إطارات متعاقبة بدون الحاجة لـ ByteTrack كامل، ويمنح كل كائن `track_id`
ثابتاً يستخدمه theft_logic.py لقياس مدة البقاء في كل منطقة.

يتتبّع أيضاً علاقة كل منتج باليد لكل إطار (قرب/تراكب) لتحديد ما إذا "التُقِط"
(picked_up) بيد أثناء وجوده في Zone 1 ثم "أُفلِت" (released) لاحقاً — انظر
الحقول على TrackedObject أدناه. theft_logic.py يستخدم هذا لمنع التنبيه على
كائن لم يُلتقط بيد أبداً (لا صلة له بسرقة) أو ما زال ممسوكاً.

الحالة محفوظة لكل جلسة (session_id) بشكل منفصل حتى لا تتداخل العربات
المتزامنة مع بعضها.
"""
import time
from typing import Dict, List, Optional

from cv import config as cv_config
from cv import zones


def _iou(box_a, box_b) -> float:
    """Intersection-over-Union بين صندوقين [x1,y1,x2,y2]. يُرجع 0.0-1.0."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _expand_box(box, margin_ratio: float):
    """يوسّع صندوقاً بنسبة margin_ratio من أبعاده في كل اتجاه."""
    x1, y1, x2, y2 = box
    mx = (x2 - x1) * margin_ratio
    my = (y2 - y1) * margin_ratio
    return (x1 - mx, y1 - my, x2 + mx, y2 + my)


def _boxes_intersect(box_a, box_b) -> bool:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


def _hand_near_product(hand_box, product_box, margin_ratio: float) -> bool:
    """صحيح إذا كان صندوق اليد يتراكب مع صندوق المنتج (بعد توسيع الأخير
    بهامش صغير) — أي أن اليد تلامس/تمسك المنتج تقريباً."""
    return _boxes_intersect(hand_box, _expand_box(product_box, margin_ratio))


class TrackedObject:
    """كائن منتج واحد متتبَّع عبر الإطارات. يحتفظ بالمنطقة الحالية، وقت
    الدخول إلى Zone 1، وعلاقته باليد (التُقِط ثم أُفلِت؟) حتى يمكن حساب
    مدة البقاء وتحديد أهليته لتنبيه UNSCANNED_IN_CART."""
    _id_counter = 0

    def __init__(self, xyxy, label: str, frame_height: int):
        TrackedObject._id_counter += 1
        self.track_id = TrackedObject._id_counter
        self.box = xyxy
        self.label = label
        self.last_seen = time.time()
        self.zone1_entry_time: Optional[float] = None
        self.in_cart_zone = False

        # علاقة اليد بالمنتج — انظر update_hand_proximity()
        self.hand_near = False
        self.picked_up = False   # لُوحظ قرب يد أثناء وجوده في Zone 1
        self.released = False    # التُقِط ثم ابتعدت اليد عنه لاحقاً (مرة واحدة، لا يُلغى)

        self._update_zone(xyxy, frame_height)

    def _update_zone(self, xyxy, frame_height: int):
        _, cy = zones.bbox_center(xyxy)
        zone = zones.classify_point(cy, frame_height)
        if zone == "scan":
            if self.zone1_entry_time is None:
                self.zone1_entry_time = time.time()
            self.in_cart_zone = False
        else:
            self.zone1_entry_time = None
            self.in_cart_zone = True

    def update(self, xyxy, frame_height: int):
        self.box = xyxy
        self.last_seen = time.time()
        self._update_zone(xyxy, frame_height)

    def update_hand_proximity(self, hand_near: bool):
        """يُستدعى مرة كل إطار تم فيه رصد هذا الكائن، بعد تحديث موقعه/منطقته."""
        self.hand_near = hand_near
        if not self.in_cart_zone and hand_near:
            self.picked_up = True
        if self.picked_up and not hand_near:
            self.released = True

    @property
    def zone1_duration(self) -> float:
        if self.zone1_entry_time is None:
            return 0.0
        return time.time() - self.zone1_entry_time


class Tracker:
    def __init__(self):
        # session_id -> {track_id -> TrackedObject}
        self._tracked: Dict[int, Dict[int, TrackedObject]] = {}

    def update(self, session_id: int, detections: List[dict], frame_height: int) -> Dict[int, TrackedObject]:
        """
        يطابق اكتشافات هذا الإطار (فئة "product" فقط) مع الكائنات المتتبَّعة
        باستخدام IoU. ينشئ كائنات جديدة للاكتشافات غير المطابقة، ويحذف
        الكائنات التي لم تُشاهَد منذ أكثر من ثانيتين (غادرت الإطار).
        كما يحدّث علاقة كل كائن مرصود هذا الإطار باليد (قرب/انفصال) بالاعتماد
        على اكتشافات فئة "hand" في نفس الإطار.
        يُرجع dict الجلسة الحالي {track_id -> TrackedObject}.
        """
        tracked = self._tracked.setdefault(session_id, {})
        now = time.time()

        stale = [tid for tid, obj in tracked.items() if now - obj.last_seen > 2.0]
        for tid in stale:
            del tracked[tid]

        product_detections = [d for d in detections if d.get("category") == "product"]
        hand_boxes = [d["xyxy"] for d in detections if d.get("category") == "hand"]
        matched_track_ids = set()

        for det in product_detections:
            best_iou = cv_config.IOU_MATCH_THRESHOLD
            best_tid = None
            for tid, obj in tracked.items():
                if tid in matched_track_ids:
                    continue
                iou = _iou(det["xyxy"], obj.box)
                if iou > best_iou:
                    best_iou = iou
                    best_tid = tid

            if best_tid is not None:
                tracked[best_tid].update(det["xyxy"], frame_height)
                matched_track_ids.add(best_tid)
            else:
                new_obj = TrackedObject(det["xyxy"], det["label"], frame_height)
                tracked[new_obj.track_id] = new_obj
                matched_track_ids.add(new_obj.track_id)

        # علاقة اليد بالمنتج — فقط للكائنات المرصودة فعلياً هذا الإطار
        for tid in matched_track_ids:
            obj = tracked[tid]
            hand_near = any(
                _hand_near_product(hb, obj.box, cv_config.HAND_PRODUCT_PROXIMITY_MARGIN)
                for hb in hand_boxes
            )
            obj.update_hand_proximity(hand_near)

        return tracked

    def get_tracked(self, session_id: int) -> Dict[int, TrackedObject]:
        return self._tracked.get(session_id, {})

    def clear_session(self, session_id: int):
        self._tracked.pop(session_id, None)
