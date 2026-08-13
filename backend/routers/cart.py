"""
routers/cart.py
===============
إدارة العربات الفيزيائية (Cart RFID registry).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from core.rfid_utils import normalize_rfid
from models.cart import Cart, CartStatus
from models.user import User
from schemas import CartOut
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CartUpdate(BaseModel):
    cart_number: Optional[str] = None
    rfid_uid:    Optional[str] = None


@router.get("/", response_model=list)
def list_carts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    carts = db.query(Cart).all()
    return [CartOut(
        id=c.id, cart_number=c.cart_number,
        rfid_uid=c.rfid_uid, status=c.status.value,
    ) for c in carts]


@router.post("/register", response_model=CartOut, status_code=201)
def register_cart(
    cart_number: str,
    rfid_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تسجيل عربة جديدة مع RFID UID."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    rfid_uid = normalize_rfid(rfid_uid)
    if db.query(Cart).filter(Cart.rfid_uid == rfid_uid).first():
        raise HTTPException(400, "RFID already registered to another cart")
    if db.query(Cart).filter(Cart.cart_number == cart_number).first():
        raise HTTPException(400, "Cart number already exists")
    cart = Cart(cart_number=cart_number, rfid_uid=rfid_uid, status=CartStatus.ACTIVE)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return CartOut(id=cart.id, cart_number=cart.cart_number,
                   rfid_uid=cart.rfid_uid, status=cart.status.value)


@router.put("/{cart_id}", response_model=CartOut)
def update_cart(
    cart_id: int,
    req: CartUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تعديل بيانات العربة — رقمها أو RFID UID."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")

    if req.rfid_uid:
        new_rfid = normalize_rfid(req.rfid_uid)
        if new_rfid != cart.rfid_uid:
            existing = db.query(Cart).filter(Cart.rfid_uid == new_rfid).first()
            if existing:
                raise HTTPException(400, "RFID already registered to another cart")
            cart.rfid_uid = new_rfid

    if req.cart_number and req.cart_number != cart.cart_number:
        existing = db.query(Cart).filter(Cart.cart_number == req.cart_number).first()
        if existing:
            raise HTTPException(400, "Cart number already exists")
        cart.cart_number = req.cart_number

    db.commit()
    db.refresh(cart)
    return CartOut(id=cart.id, cart_number=cart.cart_number,
                   rfid_uid=cart.rfid_uid, status=cart.status.value)


@router.delete("/{cart_id}", status_code=204)
def delete_cart(
    cart_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """حذف عربة — فقط إذا لم تكن في جلسة نشطة."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found")

    # التحقق من عدم وجود جلسة نشطة
    from models.session import ShoppingSession
    from models.cart import CartStatus as CS
    active = db.query(ShoppingSession).filter(
        ShoppingSession.cart_id == cart_id,
        ShoppingSession.status.in_([CS.ACTIVE, CS.PENDING_PAYMENT, CS.PAYMENT_IN_PROGRESS])
    ).first()
    if active:
        raise HTTPException(409, "Cannot delete cart with an active session")

    db.delete(cart)
    db.commit()