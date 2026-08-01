"""
cv/alert_handler.py
====================
الجسر بين محرّك الرؤية الحاسوبية (cv/theft_logic.py) وباقي النظام.

يُسجَّل كـ callback عبر `theft_service.set_theft_callback(handle_theft_alert)`
في main.py عند بدء التشغيل. يُستدعى تلقائياً من theft_logic.py في كل مرة
يُطلَق فيها تنبيه جديد (PROLONGED_HOLDING أو UNSCANNED_IN_CART).

سير العمل المطلوب (بالضبط كما وُصف):
  1. منتج دخل السلة (Zone 2) دون تسجيل مسح → alert_type=UNSCANNED_IN_CART.
  2. يُسجَّل الحدث بقاعدة البيانات (TheftLog) بدون تفعيل الفرامل بعد.
  3. تُرسَل شاشة حمراء منبثقة لنقطة بيع العميل (WebSocket) تحمل مهلة
     CART_BRAKE_GRACE_SECONDS (افتراضياً 10 ثواني) لإعادة مسح المنتج.
  4. تُرسَل إشعار فوري للوحة تحكم الأدمن (WebSocket) يحمل session_id/cart_id
     — تُستخدَم من AdminNotifications.jsx لعرض زر "الانتقال للخريطة".
  5. تبدأ مهلة عدّ تنازلي فعلية على الخادم (asyncio). إن سُجِّل مسح باركود
     لنفس الجلسة خلال المهلة (عبر theft_service.register_scanned_product
     المستدعاة من routers/session.py) → يُلغى التصعيد وتُرسَل رسالة
     "theft_alert_cleared" لإغلاق الشاشة الحمراء.
  6. إن لم يُعَد المسح خلال المهلة → يُرسَل أمر تفعيل الفرامل عبر MQTT
     (4 سيرفوهات متصلة بدرايفر على الراسبيري باي)، ويُسجَّل حدث جديد
     بقاعدة البيانات بـ brake_activated=True، وتُرسَل رسائل WebSocket
     لكل من نقطة البيع (قفل العربة) ولوحة الأدمن (تصعيد التنبيه).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("neoshop.cv.alert_handler")

# مهام التصعيد الجارية حالياً — session_id -> asyncio.Task
# تُستخدَم لإلغاء مهلة سابقة لو وصل تنبيه جديد لنفس الجلسة قبل انتهائها.
_pending_escalations: dict = {}


async def handle_theft_alert(session_id: int, alert: dict):
    """Callback مسجَّل لدى theft_service — يُستدعى عند كل تنبيه جديد من الكاميرا."""
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.theft import TheftLog
    from websocket_router import manager as ws_manager
    from mqtt.client import mqtt_service
    from core.config import settings
    from cv import scan_events

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            log.warning(f"[CV] Alert for unknown session {session_id}: {alert}")
            return

        cart_rfid = session.cart_rfid or ""
        cart_id   = session.cart_id

        # ── 1) تسجيل الحدث بقاعدة البيانات ──────────────────────────────────
        log_entry = TheftLog(
            session_id=session_id,
            alert_type=alert.get("alert_type", "UNSCANNED_IN_CART"),
            description=alert.get("description"),
            confidence_score=alert.get("confidence_score"),
            brake_activated=False,
            customer_notified=True,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        is_spatial = alert.get("trigger") == "spatial"  # UNSCANNED_IN_CART فقط
        grace_seconds = settings.CART_BRAKE_GRACE_SECONDS if is_spatial else None

        base_payload = {
            "alert_id":    log_entry.id,
            "session_id":  session_id,
            "cart_id":     cart_id,
            "cart_rfid":   cart_rfid,
            "alert_type":  alert.get("alert_type"),
            "description": alert.get("description"),
            "object_class": alert.get("object_class"),
            "zone":        alert.get("zone"),
            "grace_seconds": grace_seconds,
            "brake_activated": False,
        }

        # ── 2) شاشة حمراء منبثقة على نقطة البيع (فقط لتنبيهات السلة الفعلية) ─
        await ws_manager.broadcast_to_session(session_id, {
            "type": "theft_alert",
            "data": base_payload,
        })

        # ── 3) إشعار فوري للوحة الأدمن (مع زر "الانتقال للخريطة") ──────────
        await ws_manager.broadcast_to_admin({
            "type": "theft_alert",
            "data": base_payload,
        })

        # ── 4) مهلة إعادة المسح + تصعيد تلقائي للفرامل ──────────────────────
        if is_spatial:
            # ألغِ أي مهلة سابقة لنفس الجلسة لتفادي تصعيدين متزامنين
            old_task = _pending_escalations.get(session_id)
            if old_task and not old_task.done():
                old_task.cancel()

            task = asyncio.create_task(
                _grace_period_and_escalate(session_id, log_entry.id, grace_seconds)
            )
            _pending_escalations[session_id] = task

    except Exception as e:
        log.error(f"[CV] handle_theft_alert error: {e}")
        db.rollback()
    finally:
        db.close()


async def _grace_period_and_escalate(session_id: int, alert_id: int, grace_seconds: float):
    """
    ينتظر `grace_seconds` ثم يتحقق: هل سُجِّل مسح باركود لهذه الجلسة خلال
    المهلة؟ إن لا — يُفعِّل الفرامل فعلياً (MQTT) ويُصعِّد التنبيه.
    إن نعم — يُرسل "theft_alert_cleared" لإغلاق الشاشة الحمراء بهدوء.
    """
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.theft import TheftLog
    from websocket_router import manager as ws_manager
    from mqtt.client import mqtt_service
    from cv import scan_events

    alert_started_at = datetime.now(timezone.utc)
    try:
        await asyncio.sleep(grace_seconds)
    except asyncio.CancelledError:
        # وصل تنبيه أحدث لنفس الجلسة — هذه المهلة لم تعد ذات صلة
        return

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            return

        rescanned = scan_events.has_recent_scan(session_id, grace_seconds + 1.0)

        if rescanned:
            # ✅ العميل أعاد مسح المنتج في الوقت المحدد — إلغاء التصعيد
            await ws_manager.broadcast_to_session(session_id, {
                "type": "theft_alert_cleared",
                "data": {"session_id": session_id, "alert_id": alert_id},
            })
            await ws_manager.broadcast_to_admin({
                "type": "theft_alert_cleared",
                "data": {"session_id": session_id, "alert_id": alert_id},
            })
            log.info(f"[CV] Session {session_id}: rescanned in time — alert cleared")
            return

        # ⛔ لم يُعَد المسح خلال المهلة → تفعيل فرامل العربة (4 سيرفوهات عبر
        # الدرايفر على الراسبيري باي) عبر MQTT
        cart_rfid = session.cart_rfid or ""
        brake_sent = mqtt_service.publish_brake_command(cart_rfid, True) if cart_rfid else False

        escalated_log = TheftLog(
            session_id=session_id,
            alert_type="BRAKE_ACTIVATED",
            description=(
                f"لم يُعَد مسح المنتج خلال {int(grace_seconds)} ثوانٍ — "
                f"تم إرسال أمر تفعيل فرامل العربة"
            ),
            confidence_score=1.0,
            brake_activated=True,
            customer_notified=True,
            security_notified=True,
        )
        db.add(escalated_log)
        db.commit()
        db.refresh(escalated_log)

        # قفل حالة العربة (يُستهلَك من نفس آلية cart_locked الموجودة أصلاً
        # بالـ Frontend — POSPage.jsx وAdminSecurity)
        await ws_manager.set_cart_locked(session_id, True)

        payload = {
            "alert_id":   escalated_log.id,
            "session_id": session_id,
            "cart_id":    session.cart_id,
            "cart_rfid":  cart_rfid,
            "alert_type": "BRAKE_ACTIVATED",
            "description": escalated_log.description,
            "brake_activated": True,
            "brake_command_sent": brake_sent,
        }
        await ws_manager.broadcast_to_session(session_id, {"type": "theft_alert", "data": payload})
        await ws_manager.broadcast_to_admin({"type": "theft_alert", "data": payload})

        log.warning(
            f"[CV] Session {session_id}: NOT rescanned in {grace_seconds}s — "
            f"brake command sent (mqtt_ok={brake_sent})"
        )
    except Exception as e:
        log.error(f"[CV] _grace_period_and_escalate error: {e}")
        db.rollback()
    finally:
        db.close()
        _pending_escalations.pop(session_id, None)
