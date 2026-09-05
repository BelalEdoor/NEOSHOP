"""
routers/navigation.py
=====================
نظام تحديد موقع واتجاه العربة عبر علامات ArUco.

ترتيب العلامات:
  الممر الأول  : علامة 0 (بداية) ← علامة 1 (نهاية)
  الممر الثاني : علامة 2 (بداية) ← علامة 3 (نهاية)

منطق الاتجاه:
  - قرأ 0 ثم 1 → forward  (دخل من البداية، خرج من النهاية) → سهم يمين →
  - قرأ 1 ثم 0 → backward (دخل من النهاية، خرج من البداية) → سهم يسار ←
  - قرأ 2 ثم 3 → forward
  - قرأ 3 ثم 2 → backward
  - قرأ نفس العلامة مرتين متتاليتين (0,0 / 1,1 / 2,2 / 3,3) → دخل ثم رجع
    وخرج من نفس نقطة الدخول (لم يقطع الممر إطلاقاً) → in_aisle=False فوراً

  - أي علامة أخرى غير 0/1/2/3 (أي: ليست بحدود ممر) تُعامل كعلامة "قسم
    منتجات": تُبحث بجدول Section عبر marker_id، وإذا وُجدت، تُحدَّث
    current_section_id / pos_x / pos_y للعربة مباشرة (العربة خرجت من
    الممر ووقفت عند قسم محدد).

Endpoints:
  GET  /api/navigation/map
  GET  /api/navigation/cart/{cart_id}
  GET  /api/navigation/carts         ← كل العربات النشطة (لخريطة الأدمن)
  GET  /api/navigation/cart/{cart_id}/monitor  ← جديد: تفاصيل مراقبة العربة
                                                  (الحساب + الفاتورة الحالية)
  POST /api/navigation/marker-read
  GET  /api/navigation/sections
  GET  /api/navigation/log/{cart_id}
  GET  /api/navigation/path          ← مسار من العربة إلى منتج
"""
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.map import Section, Shelf, CartLiveStatus, MarkerReadLog
from models.cart import Cart
from models.session import ShoppingSession
from models.user import User
from models.product import Product
from websocket_router import manager as ws_manager

router = APIRouter()

NAV_DEVICE_KEY = os.getenv("NAV_DEVICE_KEY", "neoshop-pi-secret-key")

STORE_WIDTH_M = float(os.getenv("STORE_WIDTH_M", "12"))
STORE_DEPTH_M = float(os.getenv("STORE_DEPTH_M", "8"))


# ── خريطة العلامات ────────────────────────────────────────────────────────────
# كل ممر له علامة بداية وعلامة نهاية
# الممر الأول:  0 (بداية) و 1 (نهاية)
# الممر الثاني: 2 (بداية) و 3 (نهاية)

AISLE_MAP = {
    # marker_id → (aisle_id, is_start)
    0: (1, True),   # ممر 1 بداية
    1: (1, False),  # ممر 1 نهاية
    2: (2, True),   # ممر 2 بداية
    3: (2, False),  # ممر 2 نهاية
}

# موقع كل ممر على الخريطة (للواجهة الأمامية)
AISLE_POSITIONS = {
    1: {"label_ar": "الممر الأول",  "label_en": "Aisle 1"},
    2: {"label_ar": "الممر الثاني", "label_en": "Aisle 2"},
}


def _verify_device(x_device_key: Optional[str] = Header(None)):
    if x_device_key != NAV_DEVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid device key")


def _naive(dt):
    """إزالة معلومات المنطقة الزمنية للمقارنة المتسقة بين SQLite و MySQL."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


# ── Schemas ───────────────────────────────────────────────────────────────────

class MarkerReadRequest(BaseModel):
    cart_id:   int
    marker_id: int

class CartPositionOut(BaseModel):
    cart_id:            int
    cart_number:        Optional[str]     = None   # المعرّف المطبوع على العربة، e.g. "CART-001"
    last_marker_id:     Optional[int]     = None
    aisle_id:           Optional[int]     = None
    in_aisle:           bool              = False
    direction:          Optional[str]     = None   # 'forward' | 'backward' | None (بعد اكتمال الحركة)
    entry_direction:    Optional[str]     = None   # اتجاه متوقّع فور الدخول للممر (قبل اكتمال الحركة)
    section_name:       Optional[str]     = None
    current_section_id: Optional[int]     = None   # ← جديد: القسم الحالي (لو العربة واقفة عند قسم)
    pos_x:              Optional[float]   = None   # ← جديد: إحداثي X على الخريطة
    pos_y:              Optional[float]   = None   # ← جديد: إحداثي Y على الخريطة
    updated_at:         Optional[datetime] = None

class PathRequest(BaseModel):
    cart_id:   int
    shelf_key: str   # e.g. "A1", "C2"

class PathStep(BaseModel):
    type:    str   # 'current' | 'aisle' | 'shelf'
    label:   str
    detail:  Optional[str] = None

class PathOut(BaseModel):
    steps:       List[PathStep]
    instruction: str   # نص توجيهي مختصر للعميل
    direction:   Optional[str] = None


class CartMonitorUser(BaseModel):
    id:        int
    name:      str
    email:     str
    is_active: bool


class CartMonitorItem(BaseModel):
    product_id: int
    name:       str
    name_ar:    Optional[str] = None
    quantity:   int
    unit_price: float
    line_total: float


class CartMonitorOut(BaseModel):
    cart_id:        int
    cart_number:    Optional[str] = None
    session_id:     Optional[int] = None
    session_status: Optional[str] = None
    started_at:     Optional[datetime] = None
    total_amount:   float = 0.0
    user:           Optional[CartMonitorUser] = None
    items:          List[CartMonitorItem] = []
    camera_stream_path: str = "/api/camera/stream"   # الفرونت يلحق ?token=... و ?cart_id=...


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/map")
def get_map(db: Session = Depends(get_db)):
    sections = db.query(Section).all()
    return {
        "store_width_m": STORE_WIDTH_M,
        "store_depth_m": STORE_DEPTH_M,
        "sections": [
            {"id": s.section_id, "name": s.name,
             "marker_id": s.marker_id, "map_x": s.map_x, "map_y": s.map_y}
            for s in sections
        ],
        "aisles": AISLE_POSITIONS,
    }


@router.get("/sections")
def list_sections(db: Session = Depends(get_db)):
    return [
        {"id": s.section_id, "name": s.name, "marker_id": s.marker_id}
        for s in db.query(Section).all()
    ]


def _entry_direction_of(status: CartLiveStatus) -> Optional[str]:
    """
    اتجاه مؤقّت (entry_direction): لحظة دخول العربة للممر (in_aisle=True) لا
    يكون "direction" النهائي جاهزاً بعد (يحتاج قراءة العلامة الثانية). لكن
    يمكننا توقّع الاتجاه فوراً من نوع أول علامة قُرئت: دخل من علامة البداية
    → متوقَّع forward، دخل من علامة النهاية → متوقَّع backward. هذا يُستخدم
    لعرض سهم صغير فوري بجانب مؤشر العربة على الخريطة بدل انتظار اكتمال الحركة.
    """
    if status.in_aisle and status.first_marker_id is not None:
        first_info = AISLE_MAP.get(status.first_marker_id)
        if first_info:
            _, is_start = first_info
            return "forward" if is_start else "backward"
    return None


def _status_to_out(status: CartLiveStatus, cart_number: Optional[str] = None) -> CartPositionOut:
    return CartPositionOut(
        cart_id=status.cart_id,
        cart_number=cart_number,
        last_marker_id=status.last_marker_id,
        aisle_id=status.aisle_id,
        in_aisle=status.in_aisle,
        direction=status.direction,
        entry_direction=_entry_direction_of(status),
        section_name=status.section.name if status.section else None,
        current_section_id=status.current_section_id,   # ← جديد
        pos_x=status.pos_x,                              # ← جديد
        pos_y=status.pos_y,                               # ← جديد
        updated_at=status.updated_at,
    )


@router.get("/cart/{cart_id}", response_model=CartPositionOut)
def get_cart_position(cart_id: int, db: Session = Depends(get_db)):
    """
    يُعيد الموقع والاتجاه الحالي للعربة.
    الواجهة الأمامية تستدعي هذا كل ثانية.
    """
    status = db.query(CartLiveStatus).filter(CartLiveStatus.cart_id == cart_id).first()
    if not status:
        return CartPositionOut(cart_id=cart_id)

    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    return _status_to_out(status, cart.cart_number if cart else None)


@router.get("/carts", response_model=List[CartPositionOut])
def get_all_cart_positions(db: Session = Depends(get_db)):
    """
    يُعيد موقع/اتجاه كل العربات المعروفة دفعة واحدة — تستخدمها خريطة الأدمن
    (لوحة الإدارة) لعرض كل العربات النشطة على الخريطة بنفس الوقت، بدل
    استدعاء /cart/{id} لكل عربة على حدة.
    """
    statuses = db.query(CartLiveStatus).all()
    if not statuses:
        return []

    cart_ids = [s.cart_id for s in statuses]
    carts_by_id = {c.id: c for c in db.query(Cart).filter(Cart.id.in_(cart_ids)).all()}

    return [
        _status_to_out(status, carts_by_id.get(status.cart_id).cart_number if carts_by_id.get(status.cart_id) else None)
        for status in statuses
    ]


@router.get("/cart/{cart_id}/monitor", response_model=CartMonitorOut)
def get_cart_monitor(
 cart_id: int,
 db: Session = Depends(get_db),
 current_user: User = Depends(get_current_user),
):
    """
    يُستدعى عند الضغط على نقطة عربة بخريطة الأدمن — يُعيد الحساب المسجّل على
    العربة + الفاتورة الحالية (قيد الإنشاء) عشان تُعرض بالنافذة المنبثقة
    لمراقبة العربة.
    """
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")

    # آخر جلسة على هذه العربة (نفضّل جلسة لسا شغالة إن وُجدت، وإلا آخر جلسة
    # عموماً حتى لو انتهت — أفضل من عدم عرض شيء).
    OPEN_STATUSES = ["ACTIVE", "PENDING_PAYMENT", "PAYMENT_IN_PROGRESS", "AWAITING_REFILL"]
    session = (
        db.query(ShoppingSession)
        .filter(ShoppingSession.cart_id == cart_id, ShoppingSession.status.in_(OPEN_STATUSES))
        .order_by(ShoppingSession.started_at.desc())
        .first()
    )
    if not session:
        session = (
            db.query(ShoppingSession)
            .filter(ShoppingSession.cart_id == cart_id)
            .order_by(ShoppingSession.started_at.desc())
            .first()
        )

    user_out = None
    items_out: List[CartMonitorItem] = []
    total = 0.0
    session_id = None
    session_status = None
    started_at = None

    if session:
        session_id = session.id
        session_status = session.status.value if hasattr(session.status, "value") else str(session.status)
        started_at = session.started_at

        if session.user:
            user_out = CartMonitorUser(
                id=session.user.id, name=session.user.name,
                email=session.user.email, is_active=session.user.is_active,
            )

        for item in session.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            line_total = item.unit_price * item.quantity
            total += line_total
            items_out.append(CartMonitorItem(
                product_id=item.product_id,
                name=product.name if product else f"#{item.product_id}",
                name_ar=product.name_ar if product else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_total,
            ))

    return CartMonitorOut(
        cart_id=cart_id,
        cart_number=cart.cart_number,
        session_id=session_id,
        session_status=session_status,
        started_at=started_at,
        total_amount=round(total, 2),
        user=user_out,
        items=items_out,
    )


@router.post("/marker-read")
async def marker_read(
    req: MarkerReadRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_device),
):
    """
    يُستدعى من الراسبيري باي عند قراءة علامة ArUco.

    المنطق:
    ─────────────────────────────────────────────────────────
    1. إذا لم تكن العربة في ممر (in_aisle=False):
       → سجّل العلامة كـ first_marker، ضع in_aisle=True
       → direction = None (لم تكتمل بعد)

    2. إذا كانت العربة في ممر (in_aisle=True) وقرأت علامة:
       أ. نفس الممر + علامة مختلفة (first_marker != current):
          → اكتملت الحركة، حدّد الاتجاه:
            - first=start + current=end → forward  (0→1 أو 2→3)
            - first=end + current=start → backward (1→0 أو 3→2)
          → in_aisle=False، direction محدد

       ب. نفس الممر + نفس العلامة (first_marker == current):
          → قرأ نفس العلامة مرتين متتاليتين: دخل من نفس النقطة ثم رجع
            وخرج من نفس المكان (لم يقطع الممر إطلاقاً).
          → in_aisle=False، direction=None
          (هذه الحالة كانت سابقاً تُعامَل بالغلط كـ "ممر جديد" فتبقى
          in_aisle=True ولا تختفي نقطة العربة من الواجهة — تم إصلاحها هنا)

       ج. ممر مختلف تماماً عن first_marker الحالي:
          → أعد تهيئة الممر الجديد (علامة جديدة تبدأ ممراً جديداً)

    3. أي علامة ليست بحدود ممر (mid ليست بـ AISLE_MAP، أي ليست 0/1/2/3):
       → تُعامل كعلامة "قسم منتجات". تُبحث بجدول Section عبر marker_id.
       → إذا وُجد قسم مطابق: تُحدَّث current_section_id/pos_x/pos_y للعربة
         مباشرة، وتخرج العربة من حالة "داخل ممر" (in_aisle=False).
       → إذا لم يُوجد قسم مطابق (marker_id غير مسجّل): تُتجاهل بأمان
         (فقط last_marker_id يتحدّث، بدون أي تغيير آخر).
       (هذه الحالة كانت مفقودة بالكامل سابقاً — أي علامة قسم كانت تصل
       للنقطة هذه ولا يحصل معها أي تحديث فعلي، فتبقى نقطة العربة ثابتة
       على الخريطة رغم قراءة الكاميرا للعلامة بنجاح.)
    ─────────────────────────────────────────────────────────
    """
    cart = db.query(Cart).filter(Cart.id == req.cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail=f"Cart {req.cart_id} not found")

    mid = req.marker_id
    aisle_info = AISLE_MAP.get(mid)

    status = db.query(CartLiveStatus).filter(CartLiveStatus.cart_id == req.cart_id).first()
    if not status:
        status = CartLiveStatus(cart_id=req.cart_id)
        db.add(status)

    status.last_marker_id = mid
    now = datetime.now(timezone.utc)
    direction_result = None

    if aisle_info:
        # العربة بمنتصف ممر الآن — لا تنتمي لقسم منتجات محدد لحظياً
        status.current_section_id = None

        current_aisle, is_start = aisle_info

        if not status.in_aisle:
            # ── حالة 1: دخول الممر (قراءة أولى) ────────────────────────────
            status.in_aisle          = True
            status.aisle_id          = current_aisle
            status.first_marker_id   = mid
            status.first_marker_time = now
            status.direction         = None   # لم تكتمل بعد

        elif status.aisle_id == current_aisle and status.first_marker_id == mid:
            # ── حالة 2ب: نفس العلامة قُرئت مرتين متتاليتين ──────────────────
            # دخل من هذه النقطة ثم رجع وخرج من نفس المكان — لم يقطع الممر.
            status.direction = None
            status.in_aisle  = False   # يخفي نقطة العربة فوراً من الواجهة
            status.aisle_id  = current_aisle  # يبقى محفوظاً للعرض فقط (بدون تأثير لأن in_aisle=False)

        elif status.aisle_id == current_aisle and status.first_marker_id != mid:
            # ── حالة 2أ: نفس الممر، علامة مختلفة → اكتملت الحركة ────────────
            first_info = AISLE_MAP.get(status.first_marker_id)
            if first_info:
                _, first_is_start = first_info
                if first_is_start and not is_start:
                    direction_result = "forward"   # start → end
                elif not first_is_start and is_start:
                    direction_result = "backward"  # end → start
                else:
                    direction_result = None

            status.direction = direction_result
            status.in_aisle  = False   # خرج من الممر
            status.aisle_id  = current_aisle  # احتفظ برقم الممر للواجهة

        else:
            # ── حالة 2ج: ممر مختلف تماماً → ابدأ ممراً جديداً ────────────────
            status.in_aisle          = True
            status.aisle_id          = current_aisle
            status.first_marker_id   = mid
            status.first_marker_time = now
            status.direction         = None

    else:
        # ── حالة 3: علامة قسم منتجات (وليست علامة حدود ممر) ─────────────────
        section = db.query(Section).filter(Section.marker_id == mid).first()
        if section:
            status.current_section_id = section.section_id
            status.pos_x    = section.map_x
            status.pos_y    = section.map_y
            status.in_aisle = False
            status.aisle_id = None
            status.direction = None
        # وإلا (علامة غير مسجّلة بأي قسم): تجاهلها بأمان — يبقى فقط
        # last_marker_id محدَّثاً (لأغراض التصحيح فقط)، بدون أي تأثير آخر.

    # سجّل القراءة
    db.add(MarkerReadLog(cart_id=req.cart_id, marker_id=mid))
    db.commit()
    db.refresh(status)

    # بثّ فوري لموقع العربة الجديد للوحة الأدمن (خريطة الأدمن الحيّة —
    # AdminMapPage.jsx) عشان تتحدّث نقطة العربة لحظياً بدل انتظار الـ polling.
    if ws_manager:
        try:
            await ws_manager.broadcast_to_admin({
                "type": "cart_position",
                "data": _status_to_out(status, cart.cart_number).model_dump(mode="json"),
            })
        except Exception:
            pass  # لا نفشل الطلب الأساسي بسبب مشكلة بثّ اختيارية

    return {
        "success":            True,
        "cart_id":            req.cart_id,
        "marker_id":          mid,
        "aisle_id":           status.aisle_id,
        "in_aisle":           status.in_aisle,
        "direction":          status.direction,
        "current_section_id": status.current_section_id,
        "pos_x":              status.pos_x,
        "pos_y":              status.pos_y,
    }


@router.get("/path", response_model=PathOut)
def get_path_to_product(
    cart_id:   int,
    shelf_key: str,
    db: Session = Depends(get_db),
):
    """
    يحسب المسار من موقع العربة الحالي إلى الرف المطلوب.

    خريطة الرفوف → الأقسام (النظام الجديد A / B / C):
      A (ملاصق للممر الأول)  : A1, A2, A3
      B (القسم الأوسط)       : B1, B2  — رفّان فقط، جنباً إلى جنب
      C (ملاصق للممر الثاني) : C1, C2, C3

    القسم الأوسط B الآن مقسّم لعمودين، كل عمود 3 أرفف تماماً متل A وC:
      B1 (B11, B12, B13) ملاصق للممر الثاني (تماماً متل C)
      B2 (B21, B22, B23) ملاصق للممر الأول  (تماماً متل A)
    فلو كانت العربة أصلاً بالممر القريب من الرف المطلوب ما في داعي لأي
    توجيه عبور — وهاد يمنع اقتراح مسار غير ضروري لرف قريب جداً.
    """
    # خريطة الرفوف إلى الأقسام
    SHELF_TO_SECTION = {
        "A1": "A", "A2": "A", "A3": "A",
        "B11": "B", "B12": "B", "B13": "B",
        "B21": "B", "B22": "B", "B23": "B",
        "C1": "C", "C2": "C", "C3": "C",
    }

    # الممر "القريب" لكل رف (وليس لكل قسم — B مختلطة)
    SHELF_TO_AISLE = {
        "A1": 1, "A2": 1, "A3": 1,
        "B11": 2, "B12": 2, "B13": 2,
        "B21": 1, "B22": 1, "B23": 1,
        "C1": 2, "C2": 2, "C3": 2,
    }

    AISLE_LABELS = {
        1: {"ar": "الممر الأول",  "en": "Aisle 1"},
        2: {"ar": "الممر الثاني", "en": "Aisle 2"},
    }

    # ليبل أدق من مجرد "B" — يوضّح العمود (B1 أو B2) بالضبط، متل ما بتوضّح
    # القائمة الجانبية بصفحة العميل.
    SECTION_LABELS = {
        "A": {"ar": "القسم A",  "en": "Section A"},
        "B": {"ar": "القسم B",  "en": "Section B"},
        "C": {"ar": "القسم C",  "en": "Section C"},
    }

    def _sub_label(shelf_key: str) -> str:
        if shelf_key.startswith("B1"):
            return "B1"
        if shelf_key.startswith("B2"):
            return "B2"
        return shelf_key[0]

    shelf_key = shelf_key.upper()
    target_section = SHELF_TO_SECTION.get(shelf_key)
    if not target_section:
        raise HTTPException(status_code=404, detail=f"Shelf {shelf_key} not found")

    # الحالة الحالية للعربة
    status = db.query(CartLiveStatus).filter(CartLiveStatus.cart_id == cart_id).first()
    current_direction = status.direction if status else None
    current_aisle    = status.aisle_id  if status else None
    in_aisle         = status.in_aisle  if status else False

    target_aisle  = SHELF_TO_AISLE[shelf_key]
    aisle_label   = AISLE_LABELS[target_aisle]
    section_label = SECTION_LABELS[target_section]
    sub_label     = _sub_label(shelf_key)

    # ── بناء الخطوات ─────────────────────────────────────────────────────────
    steps: List[PathStep] = []

    # الموقع الحالي
    if in_aisle and current_aisle:
        steps.append(PathStep(
            type="current",
            label=AISLE_LABELS[current_aisle]["ar"],
            detail="موقعك الحالي"
        ))
    else:
        steps.append(PathStep(type="current", label="موقعك الحالي", detail=None))

    # هل يحتاج للتوجه لممر مختلف؟
    if not in_aisle or current_aisle != target_aisle:
        steps.append(PathStep(
            type="aisle",
            label=aisle_label["ar"],
            detail=f"توجه إلى {aisle_label['ar']}"
        ))

    # القسم المطلوب (يُظهر B1/B2 بدل "B" العامة لو الهدف بالقسم الأوسط)
    section_display = sub_label if target_section == "B" else section_label["ar"]
    steps.append(PathStep(
        type="section",
        label=section_display,
        detail=f"ابحث عن القسم {section_display}"
    ))

    # الرف المطلوب
    steps.append(PathStep(
        type="shelf",
        label=f"رف {shelf_key}",
        detail=f"المنتج في رف {shelf_key}"
    ))

    # ── النص التوجيهي ─────────────────────────────────────────────────────────
    if current_direction == "forward":
        dir_hint = "واصل في نفس الاتجاه"
    elif current_direction == "backward":
        dir_hint = "عد من حيث أتيت"
    else:
        dir_hint = f"توجه إلى {aisle_label['ar']}"

    instruction = f"{dir_hint} ← {section_label['ar']} ← رف {shelf_key}"

    return PathOut(
        steps=steps,
        instruction=instruction,
        direction=current_direction,
    )


@router.get("/log/{cart_id}")
def get_cart_log(cart_id: int, limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(MarkerReadLog)
        .filter(MarkerReadLog.cart_id == cart_id)
        .order_by(MarkerReadLog.detected_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"log_id": l.log_id, "marker_id": l.marker_id, "detected_at": l.detected_at}
        for l in logs
    ]