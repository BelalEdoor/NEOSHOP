"""
routers/payment.py
==================
Payment endpoints — يُستخدم من الـ Frontend لمتابعة الدفع
وللـ ESP32 للإبلاغ عن التحديثات عبر HTTP (بديل عن MQTT عند الحاجة).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import asyncio
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.payment import Payment, PaymentStatus, PaymentTransaction
from models.invoice import Invoice, InvoiceStatus
from models.session import ShoppingSession
from models.cart import CartStatus
from models.user import User
from schemas import PaymentOut, RefillAlertOut, RefillNotificationOut
from datetime import datetime, timezone
from websocket_router import manager as ws_manager
from mqtt.client import mqtt_service


async def _publish_refill_done_with_retry(payment_id: int, attempts: int = 5, delay: float = 0.5) -> bool:
    """
    نفس mqtt_service.publish_refill_done، بس مع محاولات قصيرة متكررة
    (حتى ~2.5 ثانية إجمالاً) قبل ما نستسلم.

    السبب: paho-mqtt عنده إعادة اتصال تلقائي (reconnect_delay_set) بيبدأ
    خلال ~1 ثانية من أي انقطاع لحظي (شائع مع WiFi). لو المستخدم ضغط الزر
    بالضبط جوا هالثانية، publish() العادية بترجع False فورًا بدون ما
    تعطي فرصة لإعادة الاتصال تخلص. هالدالة بتنتظر بشكل غير حاجب
    (asyncio.sleep، مش time.sleep) بين المحاولات.
    """
    for i in range(attempts):
        if mqtt_service.publish_refill_done(payment_id):
            return True
        if i < attempts - 1:
            await asyncio.sleep(delay)
    return False

router = APIRouter()


def _require_admin(current_user: User):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")


def _to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id, invoice_id=p.invoice_id,
        total_due=p.total_due, amount_inserted=p.amount_inserted,
        change_returned=p.change_returned, pending_change=p.pending_change or 0.0,
        method=p.method.value,
        status=p.status.value, started_at=p.started_at, completed_at=p.completed_at,
    )


@router.get("/session/{session_id}", response_model=List[PaymentOut])
def get_session_payments(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """جلب سجلات الدفع لجلسة معيّنة."""
    invoice = db.query(Invoice).filter(Invoice.session_id == session_id).first()
    if not invoice:
        return []
    payments = db.query(Payment).filter(Payment.invoice_id == invoice.id).all()
    return [_to_out(p) for p in payments]


@router.post("/cancel/{payment_id}", response_model=PaymentOut)
async def cancel_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إلغاء عملية دفع جارية."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")

    payment.status = PaymentStatus.FAILED
    db.commit()

    # إعادة الجلسة للحالة السابقة (ACTIVE) أو CANCELLED
    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    if invoice:
        from models.invoice import InvoiceStatus
        invoice.status = InvoiceStatus.CANCELLED
        session = db.query(ShoppingSession).filter(ShoppingSession.id == invoice.session_id).first()
        if session:
            session.status = CartStatus.CANCELLED
    db.commit()

    return _to_out(payment)


@router.get("/status/{session_id}")
def get_payment_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """جلب حالة الدفع الحالية للجلسة."""
    session = db.query(ShoppingSession).filter(ShoppingSession.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    invoice = db.query(Invoice).filter(Invoice.session_id == session_id).first()
    payment = None
    if invoice:
        payment = db.query(Payment).filter(
            Payment.invoice_id == invoice.id
        ).order_by(Payment.id.desc()).first()

    return {
        "session_id":     session_id,
        "session_status": session.status.value,
        "invoice_code":   invoice.invoice_code if invoice else None,
        "total_amount":   invoice.total_amount if invoice else 0.0,
        "payment_status": payment.status.value if payment else None,
        "amount_inserted": payment.amount_inserted if payment else 0.0,
        "change_returned": payment.change_returned if payment else 0.0,
    }


@router.get("/pending-refills", response_model=List[RefillAlertOut])
def get_pending_refills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    كل الدفعات المتوقفة حالياً بانتظار تعبئة أنابيب العملات.
    تُستخدم من البطاقة العائمة بلوحة الأدمن عند فتح الصفحة (بجانب
    التنبيهات الحية عبر WebSocket) عشان ما تضيع تنبيهات لو صاحب المتجر
    ما كان فاتح اللوحة لحظة حدوث المشكلة.
    """
    _require_admin(current_user)

    payments = db.query(Payment).filter(
        Payment.status == PaymentStatus.AWAITING_REFILL
    ).order_by(Payment.started_at.asc()).all()

    results = []
    for p in payments:
        invoice = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        results.append(RefillAlertOut(
            payment_id=p.id,
            invoice_id=p.invoice_id,
            invoice_code=invoice.invoice_code if invoice else None,
            session_id=invoice.session_id if invoice else None,
            cart_rfid=p.cart_rfid,
            remaining_change=p.pending_change or 0.0,
            device_id=p.esp32_device_id,
            started_at=p.started_at,
        ))
    return results


@router.delete("/refill-notifications/{payment_id}")
def delete_refill_notification(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    حذف إشعار من سجل "الإشعارات" بلوحة الأدمن. لا يمسّ حالة الدفعة نفسها
    (status) — فقط يصفّر حقول التتبّع الخاصة بالتعبئة (refill_requested_at /
    refill_resolved_at / refill_amount) حتى يختفي هذا الصف من سجل
    get_refill_notifications (اللي بيفلتر على refill_requested_at IS NOT NULL).
    """
    _require_admin(current_user)

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")

    payment.refill_requested_at = None
    payment.refill_resolved_at  = None
    payment.refill_amount       = None
    db.commit()

    return {"success": True, "payment_id": payment_id}


@router.get("/refill-notifications", response_model=List[RefillNotificationOut])
def get_refill_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
):
    """
    صفحة "الإشعارات" بلوحة الأدمن — سجل كامل لكل حدث نفاد أنابيب صار،
    نشط أو منتهي، الأحدث أولاً. بعكس /pending-refills اللي بترجّع بس
    المعلّق حالياً، هاي بترجّع كل شي عنده refill_requested_at (تاريخ).
    """
    _require_admin(current_user)

    payments = db.query(Payment).filter(
        Payment.refill_requested_at.isnot(None)
    ).order_by(Payment.refill_requested_at.desc()).limit(limit).all()

    results = []
    for p in payments:
        invoice = db.query(Invoice).filter(Invoice.id == p.invoice_id).first()
        is_resolved = p.refill_resolved_at is not None
        results.append(RefillNotificationOut(
            payment_id=p.id,
            invoice_code=invoice.invoice_code if invoice else None,
            device_id=p.esp32_device_id,
            remaining_change=p.refill_amount or 0.0,
            status="resolved" if is_resolved else "pending",
            requested_at=p.refill_requested_at,
            resolved_at=p.refill_resolved_at,
        ))
    return results


@router.post("/confirm-refill/{payment_id}", response_model=PaymentOut)
async def confirm_refill(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    صاحب المتجر يضغط هذا الزر بعد ما يعبّي أنابيب العملات فعلياً.
    بينشر رسالة MQTT (refill_done) للـ ESP32 يلي بدوره بيكمّل صرف الباقي
    المتبقي فقط (مش يعيد كل شي من الأول) على نفس الفاتورة.
    """
    _require_admin(current_user)

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")

    if payment.status != PaymentStatus.AWAITING_REFILL:
        raise HTTPException(400, "This payment is not waiting for a refill")

    # إعادة الدفعة/الجلسة لحالة "قيد التقدم" — الـ ESP32 هو يلي بيقرر
    # النتيجة النهائية (نجاح كامل أو تنبيه جديد لو لسا ناقص) عبر payment/complete
    # أو payment/refill_request مرة تانية.
    payment.status = PaymentStatus.IN_PROGRESS

    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == invoice.session_id
    ).first() if invoice else None

    if session:
        session.status = CartStatus.PAYMENT_IN_PROGRESS

    db.commit()
    db.refresh(payment)

    sent = await _publish_refill_done_with_retry(payment_id)
    if not sent:
        # ما قدرنا نوصل للـ ESP32 (MQTT مقطوع) — نرجّع الحالة عشان الأدمن
        # يعرف إنه لازم يجرب تاني، بدل ما تفضل الدفعة عالقة على IN_PROGRESS
        # بدون ما توصل فعلياً.
        payment.status = PaymentStatus.AWAITING_REFILL
        if session:
            session.status = CartStatus.AWAITING_REFILL
        db.commit()
        db.refresh(payment)
        raise HTTPException(503, "MQTT broker unreachable — could not notify the payment station")

    if ws_manager and session:
        await ws_manager.broadcast_to_session(session.id, {
            "type": "refill_resolved",
            "data": {"payment_id": payment_id, "session_id": session.id},
        })

    return _to_out(payment)


@router.post("/force-reactivate/{payment_id}", response_model=PaymentOut)
async def force_reactivate(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    زر احتياطي/يدوي — لحالات "الدفعة اليتيمة": صار refill_requested_at
    (ظاهرة بسجل الإشعارات كـ "بانتظار التعبئة")، بس status الحالي مش
    AWAITING_REFILL لأي سبب (انقطاع اتصال، إعادة تشغيل الباك اند أثناء
    المعالجة، إلخ) — فما بتظهر بقائمة "تنبيهات نشطة" وما في زر عادي
    تتفاعل معه.

    بعكس /confirm-refill، هاد الـ endpoint ما بيتحقق من status الحالي —
    بينشر refill_done مباشرة لأي payment_id تعطيه إياه، ويسجّل الحل
    بالسجل. يُستخدم بحذر (أدمن بس) كحل أخير لما القائمة العادية ما
    بتعرض المشكلة.
    """
    _require_admin(current_user)

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")

    payment.status = PaymentStatus.IN_PROGRESS

    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    session = db.query(ShoppingSession).filter(
        ShoppingSession.id == invoice.session_id
    ).first() if invoice else None

    if session:
        session.status = CartStatus.PAYMENT_IN_PROGRESS

    db.commit()
    db.refresh(payment)

    sent = await _publish_refill_done_with_retry(payment_id)
    if not sent:
        raise HTTPException(503, "MQTT broker unreachable — could not notify the payment station")

    # هون منسجّل الحل يدويًا بغض النظر عن رد فعل الجهاز، لأنه أصلاً كانت
    # حالة يتيمة — الهدف تنظيف السجل، مو انتظار تأكيد تلقائي.
    payment.refill_resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(payment)

    if ws_manager and session:
        await ws_manager.broadcast_to_session(session.id, {
            "type": "refill_resolved",
            "data": {"payment_id": payment_id, "session_id": session.id},
        })

    return _to_out(payment)