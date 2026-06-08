"""
routers/invoices.py — عرض وإدارة الفواتير
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.invoice import Invoice, InvoiceStatus
from models.session import ShoppingSession
from models.cart import CartStatus
from models.user import User
from schemas import InvoiceOut

router = APIRouter()


def _to_out(inv: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=inv.id, invoice_code=inv.invoice_code,
        session_id=inv.session_id, cart_rfid=inv.cart_rfid,
        subtotal=inv.subtotal, discount=inv.discount,
        total_amount=inv.total_amount, status=inv.status.value,
        items_json=inv.items_json, created_at=inv.created_at, paid_at=inv.paid_at,
    )


@router.get("/", response_model=List[InvoiceOut])
def list_invoices(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        sessions = db.query(ShoppingSession.id).filter(
            ShoppingSession.user_id == current_user.id
        ).all()
        session_ids = [s.id for s in sessions]
        invoices = db.query(Invoice).filter(
            Invoice.session_id.in_(session_ids)
        ).order_by(Invoice.id.desc()).offset(skip).limit(limit).all()
    else:
        invoices = db.query(Invoice).order_by(Invoice.id.desc()).offset(skip).limit(limit).all()
    return [_to_out(i) for i in invoices]


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _to_out(inv)


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    حذف فاتورة — للأدمن فقط.
    يُعيد الجلسة لحالة ACTIVE حتى يمكن إعادة الاختبار.
    """
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(404, "Invoice not found")

    # إعادة الجلسة لـ ACTIVE حتى يمكن إعادة الاختبار
    if inv.session_id:
        session = db.query(ShoppingSession).filter(
            ShoppingSession.id == inv.session_id
        ).first()
        if session:
            session.status   = CartStatus.ACTIVE
            session.ended_at = None

    db.delete(inv)
    db.commit()