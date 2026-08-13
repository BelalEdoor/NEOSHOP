"""
routers/session.py
==================
إدارة جلسات التسوق — القلب النابض للنظام.

الدورة الكاملة:
  POST /sessions/start       ← العميل بدأ التسوق (يُنشئ جلسة جديدة)
  POST /sessions/{id}/scan   ← Raspberry Pi مسح باركود وأضاف منتج
  DELETE /sessions/{id}/remove/{product_id} ← إزالة منتج
  POST /sessions/{id}/finish ← العميل انتهى من التسوق → PENDING_PAYMENT
  GET  /sessions/{id}        ← جلب حالة الجلسة الحالية
  GET  /sessions/active      ← جلسة العميل النشطة الحالية
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, timezone
import json

from core.database import get_db
from core.security import get_current_user, get_client_ip, audit
from core.rfid_utils import normalize_rfid
from models.session import ShoppingSession
from models.cart import Cart, CartItem, CartStatus
from models.product import Product
from models.invoice import Invoice, InvoiceStatus
from models.user import User
from schemas import SessionOut, CartItemOut, InvoiceOut, FinishShoppingRequest
from mqtt.client import mqtt_service, Topics
from websocket_router import manager as ws_manager
from cv.theft_detection import theft_service

router = APIRouter()


def _serialize_item(item: CartItem, db: Session) -> CartItemOut:
    product = db.query(Product).filter(Product.id == item.product_id).first()
    from routers.products import _serialize as _ser_product
    return CartItemOut(
        id=item.id,
        product_id=item.product_id,
        quantity=item.quantity,
        unit_price=item.unit_price,
        product=_ser_product(product) if product else None,
        is_safe=True,
        matched_allergens=[],
    )


def _serialize_session(session: ShoppingSession, db: Session) -> SessionOut:
    items = db.query(CartItem).filter(CartItem.session_id == session.id).all()
    return SessionOut(
        id=session.id,
        user_id=session.user_id,
        cart_id=session.cart_id,
        cart_rfid=session.cart_rfid,
        status=session.status.value if hasattr(session.status, 'value') else str(session.status),
        total_amount=session.total_amount or 0.0,
        discount=session.discount or 0.0,
        started_at=session.started_at,
        ended_at=session.ended_at,
        items=[_serialize_item(i, db) for i in items],
    )


def _recalculate_total(session_id: int, db: Session) -> float:
    """إعادة حساب المجموع الكلي للجلسة."""
    items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    total = sum(i.unit_price * i.quantity for i in items)
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if session:
        session.total_amount = total
        db.commit()
    return total


@router.post("/start", response_model=SessionOut, status_code=201)
async def start_session(
    request: Request,
    cart_rfid: Optional[str] = None,
    # ⚠️ الباگ الجذري وراء كل مشاكل "الجلسة عالقة/جلستان ACTIVE بنفس الوقت"
    # التي واجهناها: الفرونت اند يرسل فعلياً `?cart_number=CART-001` وليس
    # `cart_rfid` — واسم البراميتر هنا كان `cart_rfid` فقط، فكان FastAPI
    # يتجاهل `cart_number` تماماً (غير معرَّف بالدالة)، فيبقى `cart_rfid`
    # دائماً None، فـ `cart` يبقى None، فـ cart_id/cart_rfid يُخزَّنان NULL
    # بكل جلسة، وبالتالي منطق "إلغاء الجلسات القديمة لنفس العربة" أدناه
    # (المحاط بـ `if cart:`) لا يُنفَّذ أبداً رغم أنه صحيح تماماً. الآن
    # نقبل الاسمين معاً (توافقية للخلف) ونحلّ العربة بأي منهما متوفر.
    cart_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    بدء جلسة تسوق جديدة عند تسجيل دخول العميل.
    يقبل إما cart_rfid أو cart_number (الفرونت اند الحالي يرسل الثاني).
    """
    ip = get_client_ip(request)
    cart_rfid = normalize_rfid(cart_rfid) if cart_rfid else None

    # إغلاق أي جلسة نشطة قديمة للمستخدم
    old_session = db.query(ShoppingSession).filter(
        ShoppingSession.user_id == current_user.id,
        ShoppingSession.status == CartStatus.ACTIVE,
    ).first()
    if old_session:
        old_session.status   = CartStatus.CANCELLED
        old_session.ended_at = datetime.now(timezone.utc)
        db.commit()

    # ربط العربة — بالـ RFID إن وُجد، وإلا برقم العربة (cart_number)
    cart = None
    if cart_rfid:
        cart = db.query(Cart).filter(Cart.rfid_uid == cart_rfid).first()
    if cart is None and cart_number:
        cart = db.query(Cart).filter(Cart.cart_number == cart_number).first()
        if cart and cart.rfid_uid:
            # الكاميرا/MQTT يعتمدان على cart_rfid المطبَّع، فلو العربة
            # وُجدت عبر رقمها فقط، نُكمِل تطبيع RFID الحقيقي المخزَّن لها.
            cart_rfid = normalize_rfid(cart.rfid_uid)

    # إغلاق أي جلسة نشطة قديمة *لنفس العربة* أيضاً، بغض النظر عن المستخدم —
    # وإلا ممكن يصير عندنا جلستان ACTIVE لنفس العربة (مستخدم قديم ما
    # سكّرها صح + مستخدم جديد)، وهو بالضبط اللي صار بقاعدة البيانات
    # (Session 77 و Session 101 كلاهما ACTIVE لنفس cart_id=1).
    if cart:
        stale_cart_sessions = db.query(ShoppingSession).filter(
            ShoppingSession.cart_id == cart.id,
            ShoppingSession.status == CartStatus.ACTIVE,
        ).all()
        for s in stale_cart_sessions:
            s.status   = CartStatus.CANCELLED
            s.ended_at = datetime.now(timezone.utc)
        if stale_cart_sessions:
            db.commit()

    session = ShoppingSession(
        user_id=current_user.id,
        cart_id=cart.id if cart else None,
        cart_rfid=cart_rfid,
        status=CartStatus.ACTIVE,
        total_amount=0.0,
        discount=0.0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    audit("session_start", current_user.id, ip, f"Session {session.id} started")

    # إشعار MQTT
    mqtt_service.publish_cart_status(session.id, "ACTIVE", cart_rfid or "")

    return _serialize_session(session, db)


@router.get("/active", response_model=Optional[SessionOut])
def get_active_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """جلب الجلسة النشطة الحالية للعميل."""
    session = db.query(ShoppingSession).filter(
        ShoppingSession.user_id == current_user.id,
        ShoppingSession.status == CartStatus.ACTIVE,
    ).order_by(ShoppingSession.id.desc()).first()

    if not session:
        return None
    return _serialize_session(session, db)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == session_id,
        ShoppingSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return _serialize_session(session, db)


@router.post("/{session_id}/scan", response_model=CartItemOut, status_code=201)
async def scan_product(
    session_id: int,
    barcode: str,
    quantity: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Raspberry Pi يمسح باركود ويضيف المنتج للجلسة.
    يتحقق من أن الجلسة ACTIVE وأن المنتج موجود.
    """
    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == session_id,
        ShoppingSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    # لا يمكن إضافة منتجات بعد الانتهاء من التسوق
    if session.status != CartStatus.ACTIVE:
        raise HTTPException(409, f"Cannot add items — session is {session.status.value}")

    # البحث عن المنتج بالباركود
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(404, f"Product with barcode '{barcode}' not found")

    # التحقق من المخزون
    if product.quantity is not None and product.quantity < quantity:
        raise HTTPException(409, f"Insufficient stock. Available: {product.quantity}")

    # إضافة أو تحديث العنصر في الجلسة
    existing = db.query(CartItem).filter(
        CartItem.session_id == session_id,
        CartItem.product_id == product.id,
    ).first()

    if existing:
        existing.quantity += quantity
        db.commit()
        db.refresh(existing)
        item = existing
    else:
        item = CartItem(
            session_id=session_id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    # إعادة حساب المجموع
    new_total = _recalculate_total(session_id, db)

    # إعلام محرّك كشف السرقة (cv/theft_logic.py) أن هذا المنتج مُسِح شرعاً —
    # يُلغي أي شاشة تحذير حمراء معلّقة على نقطة البيع ومهلة تفعيل الفرامل.
    #
    # ⚠️ الأولوية لـ product.cv_category (تصنيف صريح يدوي من الأدمن يطابق
    # فئات YOLO بالضبط — bottle/candy/chips/chocolate/nuts/pasta). التخمين
    # القديم (category أو name) يبقى fallback فقط لو المنتج غير مُصنَّف
    # بعد؛ كان يفشل دائماً لأي منتج اسمه عربي بالكامل (لا يحوي كلمة مثل
    # "bottle" الإنجليزية إطلاقاً) — cv_category يحل هذا نهائياً بمطابقة
    # تامة بدل تخمين نصّي تقريبي.
    theft_service.register_scanned_product(
        session_id, product.id,
        product_label=(product.cv_category or product.category or product.name),
    )

    # WebSocket update → Frontend
    await ws_manager.broadcast_to_session(session_id, {
        "type": "cart_update",
        "data": {
            "session_id":   session_id,
            "total_amount": new_total,
            "action":       "item_added",
            "product_id":   product.id,
            "product_name": product.name,
            "quantity":     item.quantity,
        },
    })

    # MQTT update → ESP32 / Admin
    mqtt_service.publish(Topics.CART_ITEMS, {
        "session_id":   session_id,
        "product_id":   product.id,
        "product_name": product.name,
        "quantity":     item.quantity,
        "total_amount": new_total,
    })

    return _serialize_item(item, db)


@router.delete("/{session_id}/remove/{product_id}", status_code=204)
async def remove_product(
    session_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إزالة منتج من الجلسة."""
    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == session_id,
        ShoppingSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.status != CartStatus.ACTIVE:
        raise HTTPException(409, "Cannot remove items from a non-active session")

    item = db.query(CartItem).filter(
        CartItem.session_id == session_id,
        CartItem.product_id == product_id,
    ).first()

    if not item:
        raise HTTPException(404, "Item not found in session")

    # نجيب المنتج *قبل* الحذف حتى نعرف فئته لإعلام محرّك كشف السرقة
    product = db.query(Product).filter(Product.id == product_id).first()

    db.delete(item)
    db.commit()

    new_total = _recalculate_total(session_id, db)

    # إعلام محرّك كشف السرقة (cv/theft_logic.py) أن هذا المنتج حُذف شرعاً من
    # الفاتورة — يُلغي أي تحذير "أُخرج من السلة ولم يُحذف" معلَّق على هذا
    # المنتج (راجع cv/receipt_monitor.py::register_removal / try_consume_removal).
    if product:
        theft_service.register_removed_product(
            session_id, product.id,
            product_label=(product.cv_category or product.category or product.name),
        )

    await ws_manager.broadcast_to_session(session_id, {
        "type": "cart_update",
        "data": {
            "session_id":   session_id,
            "total_amount": new_total,
            "action":       "item_removed",
            "product_id":   product_id,
        },
    })


@router.post("/{session_id}/finish", response_model=InvoiceOut)
async def finish_shopping(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    العميل ضغط "Finish Shopping".

    الخطوات:
    1. منع إضافة منتجات جديدة → الحالة: PENDING_PAYMENT
    2. إنشاء Invoice نهائية مع snapshot من العناصر
    3. حفظ بيانات الفاتورة في قاعدة البيانات
    4. إرسال بيانات الفاتورة إلى MQTT Broker
    5. WebSocket update للـ Frontend
    """
    ip = get_client_ip(request)

    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == session_id,
        ShoppingSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(404, "Session not found")

    if session.status != CartStatus.ACTIVE:
        raise HTTPException(409, f"Session is already {session.status.value}")

    items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    if not items:
        raise HTTPException(400, "Cannot finish an empty session")

    # إنشاء snapshot من العناصر للفاتورة
    items_snapshot = []
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        items_snapshot.append({
            "product_id":   item.product_id,
            "product_name": product.name if product else "Unknown",
            "barcode":      product.barcode if product else "",
            "unit_price":   item.unit_price,
            "quantity":     item.quantity,
            "subtotal":     item.unit_price * item.quantity,
        })

    total_amount = sum(i["subtotal"] for i in items_snapshot)

    # توليد كود الفاتورة
    from datetime import date
    today_str = date.today().strftime("%Y%m%d")
    count = db.query(Invoice).filter(
        Invoice.invoice_code.like(f"INV-{today_str}-%")
    ).count()
    invoice_code = f"INV-{today_str}-{count + 1:04d}"

    # إنشاء الفاتورة
    invoice = Invoice(
        invoice_code=invoice_code,
        session_id=session_id,
        cart_rfid=session.cart_rfid,
        subtotal=total_amount,
        discount=session.discount or 0.0,
        total_amount=total_amount - (session.discount or 0.0),
        status=InvoiceStatus.CREATED,
        items_json=json.dumps(items_snapshot, ensure_ascii=False),
    )
    db.add(invoice)

    # تحديث حالة الجلسة → PENDING_PAYMENT
    session.status   = CartStatus.PENDING_PAYMENT
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invoice)

    # تنظيف حالة تتبّع الكاميرا لهذه الجلسة (لا داعي لمتابعتها بعد انتهاء التسوق)
    theft_service.clear_session(session_id)

    audit("session_finish", current_user.id, ip,
          f"Session {session_id} finished — invoice {invoice_code}")

    # إرسال الفاتورة إلى MQTT Broker (لاستلامها لاحقاً من ESP32)
    invoice.status = InvoiceStatus.SENT
    db.commit()

    mqtt_service.publish(Topics.CART_SESSION, {
        "event":          "session_finished",
        "session_id":     session_id,
        "cart_rfid":      session.cart_rfid,
        "invoice_code":   invoice_code,
        "total_amount":   invoice.total_amount,
    })

    # WebSocket update
    await ws_manager.broadcast_to_session(session_id, {
        "type": "session_finished",
        "data": {
            "session_id":  session_id,
            "status":      "PENDING_PAYMENT",
            "invoice_code": invoice_code,
            "total_amount": invoice.total_amount,
        },
    })

    from schemas import InvoiceOut
    return InvoiceOut(
        id=invoice.id,
        invoice_code=invoice.invoice_code,
        session_id=invoice.session_id,
        cart_rfid=invoice.cart_rfid,
        subtotal=invoice.subtotal,
        discount=invoice.discount,
        total_amount=invoice.total_amount,
        status=invoice.status.value,
        items_json=invoice.items_json,
        created_at=invoice.created_at,
    )