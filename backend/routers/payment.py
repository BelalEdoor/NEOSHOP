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
from schemas import PaymentOut
from datetime import datetime, timezone
from websocket_router import manager as ws_manager

router = APIRouter()


def _to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id, invoice_id=p.invoice_id,
        total_due=p.total_due, amount_inserted=p.amount_inserted,
        change_returned=p.change_returned, method=p.method.value,
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
