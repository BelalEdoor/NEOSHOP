"""
cv/alert_handler.py
====================
الجسر بين محرّك الرؤية الحاسوبية (cv/theft_logic.py) وباقي النظام.

يُسجَّل في main.py عند بدء التشغيل عبر ثلاثة callbacks:

    theft_service.set_theft_callback(handle_theft_alert)       # نقطة البيع + DB
    theft_service.set_dashboard_callback(handle_dashboard_alert) # لوحة التحكم
    theft_service.set_brake_callback(handle_brake_command)       # الفرامل

سير العمل الكامل:
  1. منتج استقرّ داخل Zone B (السلة) دون أن تزيد الفاتورة
     ➜ alert_type = PLEASE_SCAN_PRODUCT.
       • يُسجَّل بقاعدة البيانات (TheftLog) بدون تفعيل فرامل.
       • تُرسَل شاشة حمراء لنقطة البيع فيها عدّ تنازلي ٨ ثوانٍ
         (grace_seconds قادمة من cv_config.SCAN_TIMEOUT).
       • يُرسَل إشعار للداشبورد.
  2. إن مُسِح المنتج خلال المهلة (routers/session.py::scan_product ➜
     theft_service.register_scanned_product) ➜ تُرسَل "theft_alert_cleared"
     فتُغلَق الشاشة الحمراء بهدوء ولا يحدث أي تصعيد.
  3. إن لم يُمسح خلال ٨ ثوانٍ ➜ alert_type = PRODUCT_NOT_SCANNED:
       • فحص أخير للفاتورة مباشرةً من قاعدة البيانات (حماية من مسح لم
         يمرّ بالـ hook) — إن زادت الفاتورة فعلاً يُلغى التصعيد.
       • أمر تفعيل الفرامل يُرسَل للراسبيري باي بمسارين معاً:
             MQTT   → topic security/brake
             WebSocket → نفس اتصال الكاميرا /ws/camera/{cart_rfid}
         (٤ سيرفوهات على درايفر PCA9685).
       • تُقفَل العربة (cart_locked) ويُسجَّل BRAKE_ACTIVATED بقاعدة البيانات.
       • يصل إشعار للداشبورد مع can_release=True فيظهر زر "تفعيل السلة".
  4. ضغط الموظف زر "تفعيل السلة" (routers/theft.py::release_cart)
     ➜ release_cart_brakes() تُحرّر الفرامل وتسجّل BRAKE_RELEASED.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from cv.log_colors import colorize, YELLOW, RED, GREEN, MAGENTA

log = logging.getLogger("neoshop.cv.alert_handler")


# ══════════════════════════════════════════════════════════════════════════
# 1) تنبيه نقطة البيع + تسجيل قاعدة البيانات
# ══════════════════════════════════════════════════════════════════════════
async def handle_theft_alert(session_id: int, alert: dict):
    """Callback مسجَّل لدى theft_service — يُستدعى عند كل تنبيه جديد."""
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.theft import TheftLog
    from websocket_router import manager as ws_manager

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            log.warning(f"[CV] Alert for unknown session {session_id}: {alert}")
            return

        alert_type = alert.get("alert_type", "PLEASE_SCAN_PRODUCT")
        is_alarm = alert_type == "PRODUCT_NOT_SCANNED"

        # ── تسجيل الحدث بقاعدة البيانات ────────────────────────────────
        log_entry = TheftLog(
            session_id=session_id,
            alert_type=alert_type,
            description=alert.get("description"),
            confidence_score=alert.get("confidence_score"),
            brake_activated=False,          # يُسجَّل التفعيل الفعلي بسطر منفصل
            customer_notified=True,
            security_notified=is_alarm,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        payload = _build_payload(log_entry.id, session, alert)

        # ── شاشة نقطة البيع (العميل) ───────────────────────────────────
        recipients = ws_manager.session_client_count(session_id)
        await ws_manager.broadcast_to_session_only(session_id, {
            "type": "theft_alert",
            "data": payload,
        })

        # لوق ملوَّن حسب شدّة الحدث: تحذير (PLEASE_SCAN_PRODUCT) = أصفر،
        # إنذار فعلي (PRODUCT_NOT_SCANNED) = أحمر — وباقي الأنواع افتراضي.
        color = YELLOW if alert_type == "PLEASE_SCAN_PRODUCT" else (RED if is_alarm else None)
        message = f"[CV] Session {session_id}: {alert_type} logged (#{log_entry.id})"
        log.info(colorize(message, color, bold=True) if color else message)

        # ── تشخيص "التحذير ما بيوصل نقطة البيع" ──────────────────────────
        # إن كان recipients=0، الرسالة أُرسلت لصفر أجهزة متصلة فعلياً بـ
        # /ws/cart/{session_id} (أو /ws/pos/{session_id}) لحظة الإرسال —
        # يعني المشكلة مش بالباك اند، بل إن الفرونت اند غير متصل بالـ
        # WebSocket أصلاً لهاي الجلسة تحديداً في تلك اللحظة (تحقّق من رقم
        # الجلسة بالفرونت اند يطابق session_id هنا بالضبط، ومن أن اتصال
        # WebSocket فعلاً "open" بأدوات المطوّر بالمتصفح، تبويب Network).
        if recipients == 0:
            log.warning(colorize(
                f"[CV] Session {session_id}: theft_alert sent to 0 connected clients — "
                f"POS is likely NOT connected to /ws/cart/{session_id} right now "
                f"(check session_id match + WebSocket connection state in the browser).",
                MAGENTA, bold=True,
            ))
        else:
            log.info(colorize(
                f"[CV] Session {session_id}: theft_alert delivered to {recipients} connected client(s)",
                MAGENTA,
            ))

    except Exception as e:
        log.error(f"[CV] handle_theft_alert error: {e}")
        db.rollback()
    finally:
        db.close()

    # ⚠️ تمت إزالة فحص دوري كان هنا بالإصدار السابق (يقارن مباشرة عدد
    # أسطر الفاتورة بقاعدة البيانات كل ١.٥ ثانية). تبيّن أنه خطأ: أي تغيّر
    # بعدد الأسطر — لأي منتج، حتى لو مختلف تماماً عن المنتج المعلَّق فعلاً —
    # كان يُلغي التحذير المفتوح خطأً (مثال حقيقي: مسح "chips" مرتين ألغى
    # تحذيراً مفتوحاً على "bottle" لم يُمسح إطلاقاً). الفحص الدقيق الفعلي
    # (بالفئة تحديداً، عبر receipt_monitor.try_consume) موجود أصلاً ويعمل
    # تلقائياً مع كل إطار كاميرا داخل theft_logic.py::_evaluate_pending_session
    # طوال فترة الانتظار — سريع بما يكفي بذاته، ولا حاجة لفحص إضافي بديل
    # يفتقر لمعرفة الفئة.


# ══════════════════════════════════════════════════════════════════════════
# 2) إشعار لوحة التحكم
# ══════════════════════════════════════════════════════════════════════════
async def handle_dashboard_alert(session_id: int, alert: dict):
    """
    إشعار مستقل للوحة التحكم. عند الإنذار الفعلي (PRODUCT_NOT_SCANNED)
    يحمل can_release=True فيرسم الفرونت اند زر "تفعيل السلة" بجانب الإشعار.
    """
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from websocket_router import manager as ws_manager

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            return

        is_alarm = alert.get("alert_type") == "PRODUCT_NOT_SCANNED"
        payload = _build_payload(None, session, alert)
        payload["can_release"] = is_alarm

        await ws_manager.broadcast_to_admin({
            "type": "theft_alert",
            "data": payload,
        })
    except Exception as e:
        log.error(f"[CV] handle_dashboard_alert error: {e}")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# 2.5) إلغاء تنبيه سبق وصوله لنقطة البيع (بدون أي تسجيل بقاعدة البيانات)
# ══════════════════════════════════════════════════════════════════════════
async def handle_alert_cleared(session_id: int):
    """
    Callback خفيف — يُستدعى فقط عندما يكون تحذير أصفر قد وصل فعلاً لنقطة
    البيع، ثم اتّضح لاحقاً (نفس الجولة أو بعدها بلحظات) أن الوضع سليم
    (مثال: منتج عبر A→B وفُتح له تحذير، ثم مرّ مروراً سريعاً B→A دون أن
    يستقرّ فعلاً بالسلة). لا يكتب أي سطر بقاعدة البيانات — فقط يُعلِم
    الواجهة أن تُغلق شاشة التحذير الحالية بهدوء، تماماً كما لو أن العميل
    مسح المنتج بنجاح.
    """
    from websocket_router import manager as ws_manager

    await ws_manager.broadcast_to_session(session_id, {
        "type": "theft_alert_cleared",
        "data": {"session_id": session_id},
    })
    log.info(colorize(
        f"[CV] Session {session_id}: 🧹 stale warning cleared from POS (situation resolved)",
        GREEN,
    ))


# ══════════════════════════════════════════════════════════════════════════
# 3) تفعيل الفرامل
# ══════════════════════════════════════════════════════════════════════════
async def handle_brake_command(session_id: int, alert: dict):
    """
    التصعيد النهائي: تفعيل فرامل العربة فعلياً على الراسبيري باي.
    قبل الإرسال يُعاد فحص الفاتورة من قاعدة البيانات — إن كان العميل قد
    مسح المنتج فعلاً بطريقة لم تمرّ بالـ hook، يُلغى التصعيد بالكامل.
    """
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.cart import CartItem
    from models.theft import TheftLog
    from websocket_router import manager as ws_manager
    from mqtt.client import mqtt_service
    from cv.receipt_monitor import receipt_monitor
    from cv.theft_detection import theft_service

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            return

        # ── فحص أخير قبل الفرامل — بالفئة تحديداً، مش بعدد الأسطر العام ──
        # ⚠️ كان هذا الفحص يقارن مجرّد "هل تغيّر عدد أسطر الفاتورة" —
        # عيب حقيقي: أي مسح لأي منتج آخر (حتى مختلف تماماً عن المنتج
        # المعلَّق فعلياً) كان يُلغي التصعيد خطأً (مثال حقيقي شوهد: مسح
        # "chips" مرتين ألغى تصعيداً كان على "bottle" غير المُمسوح إطلاقاً).
        # الآن يتحقق تحديداً هل يوجد رصيد مسح غير مُستهلَك لنفس فئة
        # المنتج المعلَّق تحديداً (alert['object_class']) — نفس آلية
        # الاستهلاك المستخدَمة بكل مكان آخر بالنظام.
        db_item_count = (
            db.query(CartItem).filter(CartItem.session_id == session_id).count()
        )
        receipt_monitor.sync_item_count(session_id, db_item_count)  # مزامنة إعلامية فقط

        pending_label = alert.get("object_class")
        if pending_label and receipt_monitor.try_consume(session_id, pending_label):
            log.info(colorize(
                f"[CV] Session {session_id}: ✅✅ '{pending_label}' matched on invoice at the "
                f"last moment — situation is completely fine, brake escalation cancelled",
                GREEN, bold=True,
            ))
            theft_service.acknowledge_session(session_id)
            await ws_manager.broadcast_to_session(session_id, {
                "type": "theft_alert_cleared",
                "data": {"session_id": session_id},
            })
            return

        from core.rfid_utils import normalize_rfid
        # ⚠️ التطبيع هنا إلزامي — الجهاز مسجَّل بالذاكرة (websocket_router)
        # تحت مفتاح مطبَّع (register_device بعد normalize_rfid على الـ URL)،
        # ورسائل MQTT تُقارَن من طرف الراسبيري باي بصيغة مطبَّعة أيضاً. بدونه،
        # جلسات قديمة قد يكون session.cart_rfid فيها غير مطبَّع (فيه ":" مثلاً)
        # فتُسجَّل الفرملة "ناجحة" بقاعدة البيانات دون أن تتحرك السيرفوهات فعلياً.
        cart_rfid = normalize_rfid(session.cart_rfid) if session.cart_rfid else ""

        # ── إرسال أمر التفعيل للراسبيري باي — مساران معاً ──────────────
        mqtt_ok = bool(cart_rfid) and mqtt_service.publish_brake_command(cart_rfid, True)
        ws_ok = await ws_manager.send_to_device(cart_rfid, {
            "type": "brake",
            "command": "activate",
            "session_id": session_id,
            "reason": alert.get("description"),
        }) if cart_rfid else False

        # ── تسجيل حالة الفرامل بقاعدة البيانات ─────────────────────────
        escalated_log = TheftLog(
            session_id=session_id,
            alert_type="BRAKE_ACTIVATED",
            description=(
                f"لم يُمسح المنتج ({alert.get('object_class') or '—'}) خلال المهلة — "
                f"تم إرسال أمر تفعيل فرامل العربة (mqtt={mqtt_ok}, ws={ws_ok})"
            ),
            confidence_score=1.0,
            brake_activated=True,
            customer_notified=True,
            security_notified=True,
        )
        db.add(escalated_log)
        db.commit()
        db.refresh(escalated_log)

        # ── قفل العربة على واجهة العميل ────────────────────────────────
        await ws_manager.set_cart_locked(session_id, True)

        payload = _build_payload(escalated_log.id, session, {
            **alert,
            "alert_type": "BRAKE_ACTIVATED",
            "description": escalated_log.description,
            "brake_activated": True,
        })
        payload["brake_command_sent"] = mqtt_ok or ws_ok
        payload["can_release"] = True

        await ws_manager.broadcast_to_session_only(session_id, {"type": "theft_alert", "data": payload})
        await ws_manager.broadcast_to_admin({"type": "theft_alert", "data": payload})

        log.warning(colorize(
            f"🚨 [CV] Session {session_id}: BRAKE ACTIVATED for cart '{cart_rfid}' "
            f"(mqtt={mqtt_ok}, websocket={ws_ok})",
            RED, bold=True,
        ))
    except Exception as e:
        log.error(f"[CV] handle_brake_command error: {e}")
        db.rollback()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# 4) تحرير الفرامل — زر "تفعيل السلة" بالداشبورد
# ══════════════════════════════════════════════════════════════════════════
async def release_cart_brakes(session_id: int, released_by_user_id: Optional[int] = None) -> dict:
    """
    يُستدعى من routers/theft.py عندما يضغط الموظف زر "تفعيل السلة"
    بالداشبورد — أي أن المشكلة حُلّت. يُحرّر الفرامل ويُلغي قفل العربة.
    """
    from core.database import SessionLocal
    from models.session import ShoppingSession
    from models.theft import TheftLog
    from websocket_router import manager as ws_manager
    from mqtt.client import mqtt_service
    from cv.theft_detection import theft_service

    db = SessionLocal()
    try:
        session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
        if not session:
            return {"ok": False, "detail": "Session not found"}

        from core.rfid_utils import normalize_rfid
        # نفس ملاحظة handle_brake_command أعلاه — إلزامي لتطابق مفتاح الجهاز
        # المسجَّل وقيمة MQTT التي يقارنها الراسبيري باي.
        cart_rfid = normalize_rfid(session.cart_rfid) if session.cart_rfid else ""

        mqtt_ok = bool(cart_rfid) and mqtt_service.publish_brake_command(cart_rfid, False)
        ws_ok = await ws_manager.send_to_device(cart_rfid, {
            "type": "brake",
            "command": "release",
            "session_id": session_id,
        }) if cart_rfid else False

        # ── تصفير حالة محرّك الرؤية حتى لا تُقفل العربة فوراً من جديد ──
        theft_service.acknowledge_session(session_id)

        # ── إغلاق كل التنبيهات المفتوحة لهذه الجلسة ────────────────────
        now = datetime.now(timezone.utc)
        open_alerts = db.query(TheftLog).filter(
            TheftLog.session_id == session_id,
            TheftLog.resolved == False,  # noqa: E712
        ).all()
        for entry in open_alerts:
            entry.resolved = True
            entry.resolved_at = now
            entry.resolved_by_user_id = released_by_user_id

        release_log = TheftLog(
            session_id=session_id,
            alert_type="BRAKE_RELEASED",
            description=(
                f"تم تفعيل السلة يدوياً من لوحة التحكم — تحرير الفرامل "
                f"(mqtt={mqtt_ok}, ws={ws_ok})"
            ),
            confidence_score=1.0,
            brake_activated=False,
            customer_notified=True,
            security_notified=True,
            resolved=True,
            resolved_at=now,
            resolved_by_user_id=released_by_user_id,
        )
        db.add(release_log)
        db.commit()
        db.refresh(release_log)

        # ── فك القفل وإبلاغ الجميع ─────────────────────────────────────
        await ws_manager.set_cart_locked(session_id, False)
        await ws_manager.broadcast_to_session(session_id, {
            "type": "theft_alert_cleared",
            "data": {"session_id": session_id, "alert_id": release_log.id},
        })

        log.info(colorize(
            f"✅ [CV] Session {session_id}: cart re-enabled (BRAKE RELEASED) by user "
            f"{released_by_user_id} (mqtt={mqtt_ok}, websocket={ws_ok})",
            GREEN, bold=True,
        ))
        return {
            "ok": True,
            "session_id": session_id,
            "cart_rfid": cart_rfid,
            "alert_id": release_log.id,
            "resolved_alerts": len(open_alerts),
            "mqtt_sent": mqtt_ok,
            "websocket_sent": ws_ok,
        }
    except Exception as e:
        log.error(f"[CV] release_cart_brakes error: {e}")
        db.rollback()
        return {"ok": False, "detail": str(e)}
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════
def _build_payload(alert_id: Optional[int], session, alert: dict) -> dict:
    return {
        "alert_id":        alert_id,
        "session_id":      session.id,
        "cart_id":         session.cart_id,
        "cart_rfid":       session.cart_rfid or "",
        "alert_type":      alert.get("alert_type"),
        "description":     alert.get("description"),
        "object_class":    alert.get("object_class"),
        "zone":            alert.get("zone"),
        "grace_seconds":   alert.get("grace_seconds"),
        "brake_activated": bool(alert.get("brake_activated")),
    }