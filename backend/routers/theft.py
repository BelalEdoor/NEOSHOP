"""
routers/theft.py
================
Theft Detection — تسجيل وعرض أحداث السرقة من نظام Computer Vision.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.theft import TheftLog, TheftAlertType
from models.user import User, UserRole
from schemas import TheftLogOut, TheftAlertCreate
from datetime import datetime, timezone
from websocket_router import manager as ws_manager
from mqtt.client import mqtt_service

router = APIRouter()


def _to_out(t: TheftLog) -> TheftLogOut:
    return TheftLogOut(
        id=t.id, session_id=t.session_id,
        alert_type=t.alert_type.value if hasattr(t.alert_type, 'value') else t.alert_type,
        description=t.description, confidence_score=t.confidence_score,
        brake_activated=t.brake_activated, resolved=t.resolved,
        detected_at=t.detected_at,
    )


@router.post("/alert", response_model=TheftLogOut, status_code=201)
async def create_alert(
    req: TheftAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    يُستدعى من نظام Computer Vision (الـ Backend نفسه)
    عند اكتشاف نشاط مشبوه.
    """
    log_entry = TheftLog(
        session_id=req.session_id,
        alert_type=req.alert_type.value,
        description=req.description,
        confidence_score=req.confidence_score,
        brake_activated=req.brake_activated,
        customer_notified=True,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    # WebSocket إشعار للـ Frontend والأدمن
    alert_data = {
        "type":       "theft_alert",
        "data": {
            "alert_id":         log_entry.id,
            "session_id":       req.session_id,
            "alert_type":       req.alert_type.value,
            "description":      req.description,
            "brake_activated":  req.brake_activated,
        },
    }
    if req.session_id:
        await ws_manager.broadcast_to_session(req.session_id, alert_data)
    await ws_manager.broadcast_to_admin(alert_data)

    # تفعيل الفرامل عبر MQTT إذا لزم
    if req.brake_activated:
        from models.session import ShoppingSession
        from core.rfid_utils import normalize_rfid
        session = db.query(ShoppingSession).filter(
            ShoppingSession.id == req.session_id
        ).first()
        # ⚠️ session.cart_rfid قد يكون مخزَّناً بصيغة غير مطبَّعة (جلسات قديمة
        # أُنشئت قبل إضافة normalize_rfid، أو بيانات دخلت بمسار لا يطبّعها).
        # الراسبيري باي مسجَّل بالذاكرة (websocket_router.register_device)
        # وبأي منطق مطابقة MQTT دائماً بالصيغة المطبَّعة (بدون فواصل، حروف
        # كبيرة) — فبدون التطبيع هنا، الأمر يُنشر لكن لا يطابق أبداً، فتبدو
        # الفرملة "نجحت" بالسجل رغم أن السيرفوهات لم تتحرك فعلياً.
        if session and session.cart_rfid:
            mqtt_service.publish_brake_command(normalize_rfid(session.cart_rfid), True)

    return _to_out(log_entry)


@router.get("/", response_model=List[TheftLogOut])
def list_alerts(
    skip: int = 0, limit: int = 50,
    resolved: bool = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    q = db.query(TheftLog)
    if resolved is not None:
        q = q.filter(TheftLog.resolved == resolved)
    return [_to_out(t) for t in q.order_by(TheftLog.id.desc()).offset(skip).limit(limit).all()]


@router.post("/session/{session_id}/release-cart")
async def release_cart(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    زر "تفعيل السلة" في لوحة التحكم.

    الضغط عليه يعني أن الموظف حلّ المشكلة (تمّ مسح المنتج أو إعادته)،
    فيقوم الباك اند بـ:
      1. إرسال أمر تحرير الفرامل للراسبيري باي (MQTT + WebSocket معاً).
      2. فكّ قفل العربة وإغلاق الشاشة الحمراء على نقطة البيع.
      3. تصفير حالة محرّك الرؤية للجلسة حتى لا تُقفل العربة فوراً من جديد
         بسبب نفس المنتج الموجود أصلاً داخل السلة.
      4. تعليم كل تنبيهات الجلسة المفتوحة كمحلولة + تسجيل BRAKE_RELEASED.
    """
    if current_user.email not in ADMIN_EMAILS and current_user.role != UserRole.SECURITY:
        raise HTTPException(403, "Admin or security access required")

    from cv.alert_handler import release_cart_brakes

    result = await release_cart_brakes(session_id, released_by_user_id=current_user.id)
    if not result.get("ok"):
        raise HTTPException(404, result.get("detail", "Could not release cart"))

    return {
        "message": "Cart re-enabled — brakes released",
        **result,
    }


@router.post("/session/{session_id}/brake")
async def set_brake(
    session_id: int,
    activate: bool = Query(..., description="true = تفعيل الفرامل، false = تحريرها"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    تحكّم يدوي مباشر بالفرامل من لوحة التحكم (اختباري / حالات طارئة).
    التحرير يمرّ بنفس مسار زر "تفعيل السلة" حتى لا تختلف الحالة بينهما.
    """
    if current_user.email not in ADMIN_EMAILS and current_user.role != UserRole.SECURITY:
        raise HTTPException(403, "Admin or security access required")

    from models.session import ShoppingSession
    from websocket_router import manager as ws_manager
    from cv.alert_handler import release_cart_brakes

    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    if not activate:
        return await release_cart_brakes(session_id, released_by_user_id=current_user.id)

    from core.rfid_utils import normalize_rfid
    # نفس ملاحظة create_alert أعلاه: التطبيع هنا إلزامي حتى تتطابق القيمة مع
    # مفتاح الجهاز المسجَّل بـ websocket_router (register_device) ومع ما
    # يقارنه الراسبيري باي على رسائل MQTT — بدونه send_to_device يفشل بصمت
    # (يرجع False) وقد لا يطابق أي جهاز مشترك بـ MQTT أيضاً.
    cart_rfid = normalize_rfid(session.cart_rfid) if session.cart_rfid else ""
    mqtt_ok = bool(cart_rfid) and mqtt_service.publish_brake_command(cart_rfid, True)
    ws_ok = await ws_manager.send_to_device(cart_rfid, {
        "type": "brake", "command": "activate", "session_id": session_id,
        "reason": "manual",
    }) if cart_rfid else False

    entry = TheftLog(
        session_id=session_id,
        alert_type=TheftAlertType.BRAKE_ACTIVATED.value,
        description=f"تفعيل يدوي للفرامل من لوحة التحكم بواسطة {current_user.email}",
        confidence_score=1.0,
        brake_activated=True,
        security_notified=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    await ws_manager.set_cart_locked(session_id, True)
    return {"ok": True, "alert_id": entry.id, "mqtt_sent": mqtt_ok, "websocket_sent": ws_ok}


@router.get("/devices")
def list_connected_devices(current_user: User = Depends(get_current_user)):
    """أجهزة الراسبيري باي المتصلة حالياً ببثّ الكاميرا (تشخيص سريع)."""
    from websocket_router import manager as ws_manager
    from cv.theft_detection import theft_service

    return {
        "connected_carts": ws_manager.connected_devices(),
        "mqtt_connected": mqtt_service.is_connected,
        "yolo_ready": theft_service.is_ready,
    }


@router.patch("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    log_entry = db.query(TheftLog).filter(TheftLog.id == alert_id).first()
    if not log_entry:
        raise HTTPException(404, "Alert not found")
    log_entry.resolved            = True
    log_entry.resolved_by_user_id = current_user.id
    log_entry.resolved_at         = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Alert resolved"}