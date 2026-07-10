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

Endpoints:
  GET  /api/navigation/map
  GET  /api/navigation/cart/{cart_id}
  POST /api/navigation/marker-read
  GET  /api/navigation/sections
  GET  /api/navigation/log/{cart_id}
  GET  /api/navigation/path          ← جديد: مسار من العربة إلى منتج
"""
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from models.map import Section, Shelf, CartLiveStatus, MarkerReadLog
from models.cart import Cart

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
    cart_id:         int
    last_marker_id:  Optional[int]    = None
    aisle_id:        Optional[int]    = None
    in_aisle:        bool             = False
    direction:       Optional[str]    = None   # 'forward' | 'backward' | None (بعد اكتمال الحركة)
    entry_direction: Optional[str]    = None   # اتجاه متوقّع فور الدخول للممر (قبل اكتمال الحركة)
    section_name:    Optional[str]    = None
    updated_at:      Optional[datetime] = None

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


@router.get("/cart/{cart_id}", response_model=CartPositionOut)
def get_cart_position(cart_id: int, db: Session = Depends(get_db)):
    """
    يُعيد الموقع والاتجاه الحالي للعربة.
    الواجهة الأمامية تستدعي هذا كل ثانيتين.
    """
    status = db.query(CartLiveStatus).filter(CartLiveStatus.cart_id == cart_id).first()
    if not status:
        return CartPositionOut(cart_id=cart_id)

    # ── اتجاه مؤقّت (entry_direction) ────────────────────────────────────────
    # لحظة دخول العربة للممر (in_aisle=True) لا يكون "direction" النهائي جاهزاً
    # بعد (يحتاج قراءة العلامة الثانية). لكن يمكننا توقّع الاتجاه فوراً من نوع
    # أول علامة قُرئت: دخل من علامة البداية → متوقَّع forward، دخل من علامة
    # النهاية → متوقَّع backward. هذا يُستخدم لعرض سهم صغير فوري بجانب مؤشر
    # العربة على الخريطة بدل انتظار اكتمال الحركة.
    entry_direction = None
    if status.in_aisle and status.first_marker_id is not None:
        first_info = AISLE_MAP.get(status.first_marker_id)
        if first_info:
            _, is_start = first_info
            entry_direction = "forward" if is_start else "backward"

    return CartPositionOut(
        cart_id=cart_id,
        last_marker_id=status.last_marker_id,
        aisle_id=status.aisle_id,
        in_aisle=status.in_aisle,
        direction=status.direction,
        entry_direction=entry_direction,
        section_name=status.section.name if status.section else None,
        updated_at=status.updated_at,
    )


@router.post("/marker-read")
def marker_read(
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
       أ. إذا كانت نفس الممر (first_marker + current_marker = نفس الممر):
          → اكتملت الحركة، حدّد الاتجاه:
            - first=start + current=end → forward  (0→1 أو 2→3)
            - first=end + current=start → backward (1→0 أو 3→2)
          → in_aisle=False، direction محدد
       ب. إذا كانت من ممر مختلف:
          → أعد تهيئة الممر الجديد (علامة جديدة تبدأ ممراً جديداً)
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
        current_aisle, is_start = aisle_info

        if not status.in_aisle:
            # ── حالة 1: دخول الممر (قراءة أولى) ────────────────────────────
            status.in_aisle       = True
            status.aisle_id       = current_aisle
            status.first_marker_id   = mid
            status.first_marker_time = now
            status.direction      = None   # لم تكتمل بعد

        else:
            # ── حالة 2: العربة بالفعل في ممر ────────────────────────────────
            if status.aisle_id == current_aisle and status.first_marker_id != mid:
                # نفس الممر، علامة مختلفة → اكتملت الحركة
                first_info = AISLE_MAP.get(status.first_marker_id)
                if first_info:
                    _, first_is_start = first_info
                    if first_is_start and not is_start:
                        direction_result = "forward"   # start → end
                    elif not first_is_start and is_start:
                        direction_result = "backward"  # end → start
                    else:
                        direction_result = None

                status.direction   = direction_result
                status.in_aisle    = False   # خرج من الممر
                status.aisle_id    = current_aisle  # احتفظ برقم الممر للواجهة
            else:
                # ممر مختلف أو نفس العلامة → ابدأ ممراً جديداً
                status.in_aisle          = True
                status.aisle_id          = current_aisle
                status.first_marker_id   = mid
                status.first_marker_time = now
                status.direction         = None

    # سجّل القراءة
    db.add(MarkerReadLog(cart_id=req.cart_id, marker_id=mid))
    db.commit()

    return {
        "success":   True,
        "cart_id":   req.cart_id,
        "marker_id": mid,
        "aisle_id":  status.aisle_id,
        "in_aisle":  status.in_aisle,
        "direction": status.direction,
    }


@router.get("/path", response_model=PathOut)
def get_path_to_product(
    cart_id:   int,
    shelf_key: str,
    db: Session = Depends(get_db),
):
    """
    يحسب المسار من موقع العربة الحالي إلى الرف المطلوب.

    خريطة الرفوف → الأقسام:
      SEC1 (الأيمن)  : A1, A2, B1
      SEC2 (الأوسط) : B2, C1, C2
      SEC3 (الأيسر) : D1, D2, E1

    خريطة الأقسام → الممرات:
      للوصول لـ SEC1 → استخدم الممر الأول  (بين SEC1 وSEC2)
      للوصول لـ SEC2 → استخدم الممر الأول أو الثاني
      للوصول لـ SEC3 → استخدم الممر الثاني (بين SEC2 وSEC3)
    """
    # خريطة الرفوف إلى الأقسام
    SHELF_TO_SECTION = {
        "A1": "SEC1", "A2": "SEC1", "B1": "SEC1",
        "B2": "SEC2", "C1": "SEC2", "C2": "SEC2",
        "D1": "SEC3", "D2": "SEC3", "E1": "SEC3",
    }

    # أي ممر للوصول لكل قسم (حسب اتجاه الحركة)
    SECTION_TO_AISLE = {
        "SEC1": 1,  # الممر الأول
        "SEC2": 1,  # الممر الأول أو الثاني (نختار الأول افتراضياً)
        "SEC3": 2,  # الممر الثاني
    }

    AISLE_LABELS = {
        1: {"ar": "الممر الأول",  "en": "Aisle 1"},
        2: {"ar": "الممر الثاني", "en": "Aisle 2"},
    }

    SECTION_LABELS = {
        "SEC1": {"ar": "القسم 1 (الأيمن)",  "en": "Section 1 (Right)"},
        "SEC2": {"ar": "القسم 2 (الأوسط)", "en": "Section 2 (Middle)"},
        "SEC3": {"ar": "القسم 3 (الأيسر)",  "en": "Section 3 (Left)"},
    }

    shelf_key = shelf_key.upper()
    target_section = SHELF_TO_SECTION.get(shelf_key)
    if not target_section:
        raise HTTPException(status_code=404, detail=f"Shelf {shelf_key} not found")

    # الحالة الحالية للعربة
    status = db.query(CartLiveStatus).filter(CartLiveStatus.cart_id == cart_id).first()
    current_direction = status.direction if status else None
    current_aisle    = status.aisle_id  if status else None
    in_aisle         = status.in_aisle  if status else False

    target_aisle  = SECTION_TO_AISLE[target_section]
    aisle_label   = AISLE_LABELS[target_aisle]
    section_label = SECTION_LABELS[target_section]

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

    # القسم المطلوب
    steps.append(PathStep(
        type="section",
        label=section_label["ar"],
        detail=f"ابحث عن {section_label['ar']}"
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
