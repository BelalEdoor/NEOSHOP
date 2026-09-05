"""
cv/receipt_monitor.py
=====================

Keeps track of the shopping receipt (الفاتورة) per session.

⚠️ تصميم "استهلاك" (consumption) — نفس المنطق باتجاهين:

    1. مسبح "دخول" (_unconsumed): مسح باركود ناجح (إضافة) يضيف رصيداً.
       يُستهلَك عند عبور منتج A→B (دخول السلة) — راجع try_consume().

    2. مسبح "خروج" (_unconsumed_removals): حذف منتج من الفاتورة يضيف
       رصيداً. يُستهلَك عند عبور منتج B→A (خروج من السلة — إرجاع) —
       راجع try_consume_removal(). نفس فكرة عدم الحساسية للترتيب الزمني:
       سواء حذف العميل المنتج من الفاتورة قبل إخراجه فيزيائياً من السلة
       أو بعده، الاستهلاك يلتقطه بغضّ النظر عن التوقيت.
"""

import time
from collections import Counter
from typing import Dict, Optional


def _labels_match(a: str, b: str) -> bool:
    """
    مطابقة تامة (case-insensitive) — ⚠️ لم تعد substring تقريبية.

    التصميم القديم كان يقارن نصّياً تقريبياً (a in b or b in a) لأنه كان
    يقارن تسمية YOLO مباشرة مع اسم/فئة تجارية حرة (مثال: "bottle" داخل
    "Whole Milk 1L bottle"). الآن الطرفان دائماً من نفس القاموس المُحكَم
    (cv_category بقاعدة البيانات ↔ فئات YOLO بالضبط: bottle/can/chips) —
    فلا داعي للمرونة، والمطابقة التامة أضمن وتمنع تطابقات زائفة محتملة
    (مثال: "can" هي substring من "candy" — تطابق تقريبي كان يعتبرهما
    نفس الفئة خطأً؛ التامة تفرّق بينهما بشكل قاطع).
    """
    if not a or not b:
        return False
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return False
    return a == b


class ReceiptMonitor:

    def __init__(self):
        self._receipt_count: Dict[int, int] = {}
        self._last_scan_time: Dict[int, Optional[float]] = {}
        # session_id -> Counter({"bottle": 2, "chips": 1, ...})
        self._unconsumed: Dict[int, Counter] = {}
        # session_id -> Counter({"bottle": 1, ...}) — رصيد "حذف من الفاتورة"
        self._unconsumed_removals: Dict[int, Counter] = {}

    # --------------------------------------------------------
    # Called by POS after a successful barcode scan (إضافة)
    # --------------------------------------------------------

    def register_scan(self, session_id: int, product_label: Optional[str] = None):
        self._receipt_count[session_id] = self._receipt_count.get(session_id, 0) + 1
        self._last_scan_time[session_id] = time.time()

        if product_label:
            pool = self._unconsumed.setdefault(session_id, Counter())
            pool[product_label.strip().lower()] += 1

    # --------------------------------------------------------
    # Called by POS after removing an item from the invoice (حذف/إرجاع)
    # --------------------------------------------------------

    def register_removal(self, session_id: int, product_label: Optional[str] = None):
        self._receipt_count[session_id] = max(0, self._receipt_count.get(session_id, 0) - 1)
        self._last_scan_time[session_id] = time.time()

        if product_label:
            pool = self._unconsumed_removals.setdefault(session_id, Counter())
            pool[product_label.strip().lower()] += 1

    # --------------------------------------------------------
    # Called by CV logic
    # --------------------------------------------------------

    def try_consume(self, session_id: int, expected_label: str) -> bool:
        """
        استهلاك رصيد "دخول" (مسح/إضافة) — يُستخدَم لحظة عبور منتج A→B
        (دخول السلة) وأثناء فترة الانتظار اللاحقة.
        """
        return self._try_consume_pool(self._unconsumed.get(session_id), expected_label)

    def try_consume_removal(self, session_id: int, expected_label: str) -> bool:
        """
        استهلاك رصيد "خروج" (حذف من الفاتورة) — يُستخدَم لحظة عبور منتج
        B→A (خروج من السلة / إرجاع) وأثناء فترة الانتظار اللاحقة.
        """
        return self._try_consume_pool(self._unconsumed_removals.get(session_id), expected_label)

    @staticmethod
    def _try_consume_pool(pool: Optional[Counter], expected_label: str) -> bool:
        if not pool or not expected_label:
            return False
        needle = expected_label.strip().lower()
        for label, count in list(pool.items()):
            if count <= 0:
                continue
            if _labels_match(needle, label):
                pool[label] -= 1
                if pool[label] <= 0:
                    del pool[label]
                return True
        return False

    # --------------------------------------------------------

    def item_count(self, session_id: int) -> int:
        return self._receipt_count.get(session_id, 0)

    def seconds_since_last_scan(self, session_id: int) -> Optional[float]:
        ts = self._last_scan_time.get(session_id)
        return None if ts is None else time.time() - ts

    def sync_item_count(self, session_id: int, db_item_count: int):
        """
        مزامنة العدّاد مع العدد الحقيقي لأسطر الفاتورة بقاعدة البيانات.
        ⚠️ لا تعرف هذه الدالة تسمية المنتج المتغيّر (لا يوجد سياق فئة)،
        لذلك لا تُضاف لأي من المسبحين — إعلامية فقط لعدّاد العناصر.
        """
        previous = self._receipt_count.get(session_id, 0)
        self._receipt_count[session_id] = db_item_count
        if db_item_count != previous:
            self._last_scan_time[session_id] = time.time()
            return True
        return False

    # --------------------------------------------------------

    def reset(self, session_id: int):
        self._receipt_count.pop(session_id, None)
        self._last_scan_time.pop(session_id, None)
        self._unconsumed.pop(session_id, None)
        self._unconsumed_removals.pop(session_id, None)


receipt_monitor = ReceiptMonitor()