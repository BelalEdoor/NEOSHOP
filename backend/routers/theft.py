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
from models.user import User
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
        session = db.query(ShoppingSession).filter(
            ShoppingSession.id == req.session_id
        ).first()
        if session and session.cart_rfid:
            mqtt_service.publish_brake_command(session.cart_rfid, True)

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
