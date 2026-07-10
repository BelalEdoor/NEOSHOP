"""
mqtt/handlers.py
================
معالجات رسائل MQTT الواردة من ESP32 وRaspberry Pi.
كل handler يُعالج رسالة معيّنة ويُحدّث قاعدة البيانات ويُرسل WebSocket updates.
"""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from core.database import SessionLocal
from mqtt.client import mqtt_service, Topics

log = logging.getLogger("neoshop.mqtt.handlers")

# WebSocket manager يُحقَن من main.py
ws_manager = None


def setup_handlers():
    """تسجيل جميع handlers — يُستدعى مرة واحدة عند بدء التطبيق."""
    mqtt_service.subscribe(Topics.PAYMENT_REQUEST,  handle_payment_request)
    mqtt_service.subscribe(Topics.PAYMENT_COINS,    handle_coin_inserted)
    mqtt_service.subscribe(Topics.PAYMENT_BILLS,    handle_bill_inserted)
    mqtt_service.subscribe(Topics.PAYMENT_COMPLETE, handle_payment_complete)
    mqtt_service.subscribe(Topics.REFILL_REQUEST,   handle_refill_needed)
    mqtt_service.subscribe(Topics.CART_RFID,        handle_cart_rfid)
    log.info("[MQTT] All handlers registered")


async def handle_payment_request(topic: str, payload: dict):
    """
    ESP32 قرأ RFID وطلب بيانات الفاتورة.
    payload: {"cart_rfid": "ABC123", "event": "payment_request"}

    الخطوات:
    1. البحث عن الجلسة المرتبطة بـ RFID هذا بحالة PENDING_PAYMENT
    2. جلب الفاتورة
    3. إرسال بيانات الفاتورة إلى ESP32 عبر MQTT
    4. تغيير الحالة إلى PAYMENT_IN_PROGRESS
    """
    cart_rfid = payload.get("cart_rfid", "")
    if not cart_rfid:
        log.warning("[MQTT] payment_request: missing cart_rfid")
        return

    db: Session = SessionLocal()
    try:
        from models.session import ShoppingSession
        from models.cart import CartStatus
        from models.invoice import Invoice, InvoiceStatus
        from models.payment import Payment, PaymentStatus

        # البحث عن الجلسة بحالة PENDING_PAYMENT
        session = db.query(ShoppingSession).filter(
            ShoppingSession.cart_rfid == cart_rfid,
            ShoppingSession.status == CartStatus.PENDING_PAYMENT,
        ).order_by(ShoppingSession.id.desc()).first()

        if not session:
            log.warning(f"[MQTT] No PENDING_PAYMENT session for RFID={cart_rfid}")
            mqtt_service.publish(Topics.PAYMENT_STATUS, {
                "event": "no_invoice",
                "cart_rfid": cart_rfid,
                "message": "No pending invoice found",
            })
            return

        # جلب الفاتورة
        invoice = db.query(Invoice).filter(
            Invoice.session_id == session.id
        ).first()

        if not invoice:
            log.error(f"[MQTT] Session {session.id} has no invoice!")
            return

        # تحديث حالة الجلسة والفاتورة
        session.status = CartStatus.PAYMENT_IN_PROGRESS
        session.payment_started_at = datetime.now(timezone.utc)
        invoice.status = InvoiceStatus.PROCESSING

        # إنشاء سجل دفع جديد
        payment = Payment(
            invoice_id=invoice.id,
            total_due=invoice.total_amount,
            cart_rfid=cart_rfid,
            status=PaymentStatus.IN_PROGRESS,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        # إرسال بيانات الفاتورة إلى ESP32
        mqtt_service.publish_invoice_to_esp32({
            "cart_rfid":     cart_rfid,
            "invoice_id":    invoice.id,
            "invoice_code":  invoice.invoice_code,
            "session_id":    session.id,
            "total_amount":  invoice.total_amount,
            "payment_id":    payment.id,
            "items":         json.loads(invoice.items_json or "[]"),
        })

        log.info(f"[MQTT] Invoice sent to ESP32 for RFID={cart_rfid}, amount={invoice.total_amount}")

        # إشعار WebSocket للـ Frontend
        if ws_manager:
            await ws_manager.broadcast_to_session(session.id, {
                "type": "payment_started",
                "data": {"session_id": session.id, "status": "PAYMENT_IN_PROGRESS"},
            })

    except Exception as e:
        log.error(f"[MQTT] handle_payment_request error: {e}")
        db.rollback()
    finally:
        db.close()


async def handle_coin_inserted(topic: str, payload: dict):
    """
    ESP32 أبلغ عن إدخال عملة معدنية.
    payload: {"cart_rfid": "ABC", "denomination": 1.0, "count": 1, "payment_id": 5, "total_inserted": 5.0}
    """
    cart_rfid   = payload.get("cart_rfid", "")
    denomination = payload.get("denomination", 0.0)
    count        = payload.get("count", 1)
    payment_id   = payload.get("payment_id")
    total_inserted = payload.get("total_inserted", 0.0)

    if not payment_id:
        return

    db: Session = SessionLocal()
    try:
        from models.payment import Payment, PaymentTransaction, TransactionType, PaymentStatus

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return

        # تسجيل المعاملة
        txn = PaymentTransaction(
            payment_id=payment_id,
            transaction_type=TransactionType.COIN,
            denomination=denomination,
            count=count,
            total_value=denomination * count,
        )
        db.add(txn)

        # تحديث المبلغ المُدخَل
        payment.amount_inserted = total_inserted
        db.commit()

        log.info(f"[MQTT] Coin {denomination} x{count} for payment {payment_id}")

        # إشعار WebSocket
        if ws_manager:
            session_id = _get_session_id_from_payment(payment)
            if session_id:
                await ws_manager.broadcast_to_session(session_id, {
                    "type": "payment_update",
                    "data": {
                        "total_due":     payment.total_due,
                        "amount_inserted": payment.amount_inserted,
                        "remaining":     max(0, payment.total_due - payment.amount_inserted),
                    },
                })
    except Exception as e:
        log.error(f"[MQTT] handle_coin_inserted error: {e}")
        db.rollback()
    finally:
        db.close()


async def handle_bill_inserted(topic: str, payload: dict):
    """
    ESP32 أبلغ عن إدخال ورقة نقدية.
    payload: {"cart_rfid": "ABC", "denomination": 10.0, "payment_id": 5, "total_inserted": 15.0}
    """
    denomination   = payload.get("denomination", 0.0)
    payment_id     = payload.get("payment_id")
    total_inserted = payload.get("total_inserted", 0.0)

    if not payment_id:
        return

    db: Session = SessionLocal()
    try:
        from models.payment import Payment, PaymentTransaction, TransactionType

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return

        txn = PaymentTransaction(
            payment_id=payment_id,
            transaction_type=TransactionType.BILL,
            denomination=denomination,
            count=1,
            total_value=denomination,
        )
        db.add(txn)
        payment.amount_inserted = total_inserted
        db.commit()

        log.info(f"[MQTT] Bill {denomination} for payment {payment_id}")

        if ws_manager:
            session_id = _get_session_id_from_payment(payment)
            if session_id:
                await ws_manager.broadcast_to_session(session_id, {
                    "type": "payment_update",
                    "data": {
                        "total_due":       payment.total_due,
                        "amount_inserted": payment.amount_inserted,
                        "remaining":       max(0, payment.total_due - payment.amount_inserted),
                    },
                })
    except Exception as e:
        log.error(f"[MQTT] handle_bill_inserted error: {e}")
        db.rollback()
    finally:
        db.close()


async def handle_payment_complete(topic: str, payload: dict):
    """
    ESP32 أبلغ عن اكتمال الدفع وصرف الباقي.
    payload: {"cart_rfid": "ABC", "payment_id": 5, "amount_inserted": 20.0, "change_returned": 5.0}

    الخطوات:
    1. تغيير حالة الدفع إلى COMPLETED
    2. تغيير حالة الجلسة إلى PAID
    3. تغيير حالة الفاتورة إلى PAID
    4. تحديث مخزون المنتجات
    5. إرسال WebSocket update للـ Frontend
    """
    payment_id     = payload.get("payment_id")
    amount_inserted = payload.get("amount_inserted", 0.0)
    change_returned = payload.get("change_returned", 0.0)
    cart_rfid      = payload.get("cart_rfid", "")

    if not payment_id:
        log.error("[MQTT] payment_complete: missing payment_id")
        return

    db: Session = SessionLocal()
    try:
        from models.payment import Payment, PaymentStatus
        from models.invoice import Invoice, InvoiceStatus
        from models.session import ShoppingSession
        from models.cart import CartStatus
        from models.product import Product
        import json as json_module

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            log.error(f"[MQTT] Payment {payment_id} not found")
            return

        # تحديث الدفع
        payment.status          = PaymentStatus.COMPLETED
        payment.amount_inserted  = amount_inserted
        payment.change_returned  = change_returned
        payment.pending_change   = 0.0  # لو كانت الدفعة متوقفة بانتظار تعبئة، انتهى الانتظار
        payment.completed_at    = datetime.now(timezone.utc)

        # تحديث الفاتورة
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        if invoice:
            invoice.status  = InvoiceStatus.PAID
            invoice.paid_at = datetime.now(timezone.utc)

            # تحديث مخزون المنتجات
            items = json_module.loads(invoice.items_json or "[]")
            for item in items:
                product = db.query(Product).filter(Product.id == item.get("product_id")).first()
                if product:
                    product.quantity = max(0, (product.quantity or 0) - item.get("quantity", 1))

        # تحديث الجلسة
        session = db.query(ShoppingSession).filter(
            ShoppingSession.id == invoice.session_id if invoice else False
        ).first() if invoice else None

        if not session:
            session = db.query(ShoppingSession).filter(
                ShoppingSession.cart_rfid == cart_rfid,
                ShoppingSession.status.in_([CartStatus.PAYMENT_IN_PROGRESS, CartStatus.PENDING_PAYMENT])
            ).first()

        if session:
            session.status              = CartStatus.PAID
            session.ended_at            = datetime.now(timezone.utc)
            session.payment_completed_at = datetime.now(timezone.utc)

        db.commit()

        log.info(f"[MQTT] Payment {payment_id} COMPLETED — amount={amount_inserted}, change={change_returned}")

        # إشعار WebSocket
        if ws_manager and session:
            await ws_manager.broadcast_to_session(session.id, {
                "type": "payment_complete",
                "data": {
                    "session_id":      session.id,
                    "status":          "PAID",
                    "amount_inserted":  amount_inserted,
                    "change_returned":  change_returned,
                    "invoice_code":    invoice.invoice_code if invoice else None,
                },
            })
            # إشعار لوحة الأدمن
            await ws_manager.broadcast_to_admin({
                "type": "payment_complete",
                "data": {"session_id": session.id, "amount": payment.total_due},
            })

    except Exception as e:
        log.error(f"[MQTT] handle_payment_complete error: {e}")
        db.rollback()
    finally:
        db.close()


async def handle_refill_needed(topic: str, payload: dict):
    """
    ESP32 أبلغ أن أنابيب العملات نفدت أثناء إرجاع الباقي، والدفعة متوقفة
    مؤقتاً (Payment/Session لسا موجودين، مش ملغيين).
    payload: {
      "event": "refill_needed", "cart_rfid": "...", "payment_id": 5,
      "invoice_id": 3, "invoice_code": "INV-...", "session_id": 7,
      "remaining_change": 1, "device_id": "ESP32-PAYMENT-01"
    }

    الخطوات:
    1. تحديث حالة الدفعة/الجلسة إلى AWAITING_REFILL وتخزين المبلغ المتبقي
    2. إشعار WebSocket للأدمن (لوحة التحكم) — يشمل تفعيل إشعارات الموقع
    3. إشعار WebSocket للعميل الواقف قدام الجهاز (نفس القناة يلي بيتابع فيها الدفع)
    """
    payment_id       = payload.get("payment_id")
    remaining_change = payload.get("remaining_change", 0)
    invoice_code     = payload.get("invoice_code", "")
    cart_rfid        = payload.get("cart_rfid", "")
    device_id        = payload.get("device_id", "")

    if not payment_id:
        log.error("[MQTT] refill_needed: missing payment_id")
        return

    db: Session = SessionLocal()
    try:
        from models.payment import Payment, PaymentStatus
        from models.invoice import Invoice
        from models.session import ShoppingSession
        from models.cart import CartStatus

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            log.error(f"[MQTT] refill_needed: payment {payment_id} not found")
            return

        payment.status         = PaymentStatus.AWAITING_REFILL
        payment.pending_change = remaining_change
        payment.esp32_device_id = device_id or payment.esp32_device_id

        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        session = db.query(ShoppingSession).filter(
            ShoppingSession.id == invoice.session_id
        ).first() if invoice else None

        if session:
            session.status = CartStatus.AWAITING_REFILL

        db.commit()

        log.warning(
            f"[MQTT] REFILL NEEDED — payment {payment_id} "
            f"(invoice {invoice_code}), still owed {remaining_change} NIS"
        )

        alert_data = {
            "payment_id":       payment_id,
            "invoice_id":       payment.invoice_id,
            "invoice_code":     invoice_code,
            "session_id":       session.id if session else None,
            "cart_rfid":        cart_rfid,
            "remaining_change": remaining_change,
            "device_id":        device_id,
        }

        if ws_manager:
            # ملاحظة: broadcast_to_session بترسل تلقائياً نسخة للأدمن كمان،
            # فما بنكرر الإرسال يدوياً لتفادي وصول نفس التنبيه مرتين.
            if session:
                await ws_manager.broadcast_to_session(session.id, {
                    "type": "refill_needed",
                    "data": alert_data,
                })
            else:
                await ws_manager.broadcast_to_admin({
                    "type": "refill_needed",
                    "data": alert_data,
                })

    except Exception as e:
        log.error(f"[MQTT] handle_refill_needed error: {e}")
        db.rollback()
    finally:
        db.close()


async def handle_cart_rfid(topic: str, payload: dict):
    """Raspberry Pi أبلغ عن قراءة RFID للعربة."""
    cart_rfid = payload.get("cart_rfid", "")
    event     = payload.get("event", "")
    log.info(f"[MQTT] Cart RFID read: {cart_rfid}, event={event}")


def _get_session_id_from_payment(payment):
    """مساعد لجلب session_id من سجل الدفع."""
    try:
        db = SessionLocal()
        from models.invoice import Invoice
        invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
        return invoice.session_id if invoice else None
    except Exception:
        return None
    finally:
        db.close()
