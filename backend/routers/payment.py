"""
routers/payment.py
==================
Payment endpoints — يُستخدم من الـ Frontend لمتابعة الدفع
وللـ ESP32 للإبلاغ عن التحديثات عبر HTTP (بديل عن MQTT عند الحاجة).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.payment import Payment, PaymentStatus, PaymentTransaction
from models.invoice import Invoice, InvoiceStatus
from models.session import ShoppingSession
from models.cart import CartStatus
from models.user import User
from schemas import PaymentOut, RefillAlertOut
from datetime import datetime, timezone
from websocket_router import manager as ws_manager
from mqtt.client import mqtt_service

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
    تُستخدم من لوحة الأدمن عند فتح الصفحة (بجانب التنبيهات الحية عبر
    WebSocket) عشان ما تضيع تنبيهات لو صاحب المتجر ما كان فاتح اللوحة
    لحظة حدوث المشكلة.
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

    sent = mqtt_service.publish_refill_done(payment_id)
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
