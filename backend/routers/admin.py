"""
routers/admin.py
================
لوحة إدارة المتجر — تقارير المبيعات والإحصاءات.
نُقل من analysis.py القديم مع تحسينات.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.user import User
from models.session import ShoppingSession
from models.cart import CartItem
from models.product import Product
from models.payment import Payment
from models.invoice import Invoice
from models.theft import TheftLog

router = APIRouter()


def _require_admin(current_user: User):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """نظرة عامة على النظام للأدمن."""
    _require_admin(current_user)

    total_sessions  = db.query(ShoppingSession).count()
    paid_sessions   = db.query(ShoppingSession).filter(ShoppingSession.status == "PAID").count()
    total_revenue   = db.query(func.sum(Invoice.total_amount)).filter(Invoice.status == "PAID").scalar() or 0.0
    total_products  = db.query(Product).count()
    active_sessions = db.query(ShoppingSession).filter(ShoppingSession.status == "ACTIVE").count()
    theft_alerts    = db.query(TheftLog).filter(TheftLog.resolved == False).count()

    return {
        "total_sessions":  total_sessions,
        "paid_sessions":   paid_sessions,
        "active_sessions": active_sessions,
        "total_revenue":   round(total_revenue, 2),
        "total_products":  total_products,
        "pending_alerts":  theft_alerts,
    }


@router.get("/top-products")
def get_top_products(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """أكثر المنتجات مبيعاً."""
    _require_admin(current_user)

    results = (
        db.query(CartItem.product_id, func.sum(CartItem.quantity).label("total_sold"))
        .group_by(CartItem.product_id)
        .order_by(desc("total_sold"))
        .limit(limit)
        .all()
    )

    products = []
    for product_id, total_sold in results:
        p = db.query(Product).filter(Product.id == product_id).first()
        if p:
            products.append({
                "product_id": p.id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "total_sold": total_sold,
                "revenue": round(p.price * total_sold, 2),
            })
    return products


@router.get("/sales-summary")
def get_sales_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ملخص المبيعات."""
    _require_admin(current_user)
    from sqlalchemy import cast, Date
    from datetime import date, timedelta

    # المبيعات آخر 7 أيام
    seven_days = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        revenue = db.query(func.sum(Invoice.total_amount)).filter(
            func.date(Invoice.created_at) == day,
            Invoice.status == "PAID",
        ).scalar() or 0.0
        count = db.query(Invoice).filter(
            func.date(Invoice.created_at) == day,
            Invoice.status == "PAID",
        ).count()
        seven_days.append({"date": str(day), "revenue": round(revenue, 2), "count": count})

    return {"daily": seven_days}
