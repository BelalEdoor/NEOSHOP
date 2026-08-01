"""
routers/users.py — إدارة بيانات المستخدمين
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.security import get_current_user, get_client_ip, audit, hash_password, ADMIN_EMAILS
from models.user import User, UserRole
from schemas import (
    UserOut, UserUpdate,
    AdminCustomerOut, AdminCustomerUpdate, AdminPasswordReset,
    InvoiceOut,
)
import json

router = APIRouter()


def _require_admin(current_user: User):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")


def _to_out(user: User) -> UserOut:
    allergies = []
    if user.allergies:
        try:
            allergies = json.loads(user.allergies)
        except Exception:
            allergies = [a.strip() for a in user.allergies.split(",") if a.strip()]
    return UserOut(
        id=user.id, name=user.name, email=user.email,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        allergies=allergies, age=user.age, gender=user.gender,
        is_active=user.is_active, created_at=user.created_at,
        recommendations_enabled=user.recommendations_enabled,
        onboarding_completed=user.onboarding_completed,
        other_health_notes=user.other_health_notes,
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _to_out(current_user)


@router.put("/me", response_model=UserOut)
def update_me(
    req: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip = get_client_ip(request)
    for field, val in req.model_dump(exclude_unset=True).items():
        if field == "allergies" and isinstance(val, list):
            val = json.dumps(val)
        setattr(current_user, field, val)
    db.commit()
    db.refresh(current_user)
    audit("user_update", current_user.id, ip, "Profile updated")
    return _to_out(current_user)


@router.post("/{user_id}/disable", response_model=UserOut)
def disable_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    تعطيل حساب عميل — يُستخدم من نافذة "مراقبة العربة" بخريطة الأدمن عند
    حدوث نشاط مشبوه. الحساب يُقفَل فوراً: أي طلب لاحق من جلسة العميل
    (حتى لو التوكن ما زال صالحاً) يُرفض بـ 403 (راجع core/security.py).
    """
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    audit("user_disabled", current_user.id, get_client_ip(request), f"Disabled user {user_id} ({user.email})")
    return _to_out(user)


@router.post("/{user_id}/enable", response_model=UserOut)
def enable_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """إعادة تفعيل حساب عميل بعد مراجعة الحدث المشبوه."""
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = True
    db.commit()
    db.refresh(user)
    audit("user_enabled", current_user.id, get_client_ip(request), f"Enabled user {user_id} ({user.email})")
    return _to_out(user)


# ══════════════════════════════════════════════════════════════════════════════
# Admin — صفحة "حسابات العملاء" بالسايدبار (AdminCustomers.jsx)
# ══════════════════════════════════════════════════════════════════════════════

def _to_admin_out(user: User, db: Session) -> AdminCustomerOut:
    from models.session import ShoppingSession
    from models.invoice import Invoice, InvoiceStatus

    session_ids = [s.id for s in db.query(ShoppingSession.id).filter(
        ShoppingSession.user_id == user.id
    ).all()]
    total_orders = 0
    total_spent = 0.0
    if session_ids:
        paid_invoices = db.query(Invoice).filter(
            Invoice.session_id.in_(session_ids),
            Invoice.status == InvoiceStatus.PAID,
        ).all()
        total_orders = len(paid_invoices)
        total_spent = round(sum(i.total_amount for i in paid_invoices), 2)

    base = _to_out(user)
    return AdminCustomerOut(**base.model_dump(), total_orders=total_orders, total_spent=total_spent)


@router.get("/admin/customers", response_model=List[AdminCustomerOut])
def list_customers(
    q: str = Query(None, description="بحث بالاسم أو البريد الإلكتروني"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """قائمة كل حسابات العملاء (role=customer) — لصفحة حسابات العملاء بلوحة الأدمن."""
    _require_admin(current_user)
    query = db.query(User).filter(User.role == UserRole.CUSTOMER)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((User.name.ilike(like)) | (User.email.ilike(like)))
    users = query.order_by(User.id.desc()).all()
    return [_to_admin_out(u, db) for u in users]


@router.get("/admin/customers/{user_id}", response_model=AdminCustomerOut)
def get_customer_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """تفاصيل عميل واحد — بيانات الحساب + الملف الصحي + إحصاءات الطلبات."""
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id, User.role == UserRole.CUSTOMER).first()
    if not user:
        raise HTTPException(404, "Customer not found")
    return _to_admin_out(user, db)


@router.get("/admin/customers/{user_id}/invoices", response_model=List[InvoiceOut])
def get_customer_invoices(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """كل فواتير عميل معيّن — لمتابعة سجل مشترياته من لوحة الأدمن."""
    _require_admin(current_user)
    from models.session import ShoppingSession
    from models.invoice import Invoice

    session_ids = [s.id for s in db.query(ShoppingSession.id).filter(
        ShoppingSession.user_id == user_id
    ).all()]
    invoices = db.query(Invoice).filter(
        Invoice.session_id.in_(session_ids)
    ).order_by(Invoice.id.desc()).all() if session_ids else []

    return [InvoiceOut(
        id=inv.id, invoice_code=inv.invoice_code, session_id=inv.session_id,
        cart_rfid=inv.cart_rfid, subtotal=inv.subtotal, discount=inv.discount,
        total_amount=inv.total_amount, status=inv.status.value,
        items_json=inv.items_json, created_at=inv.created_at, paid_at=inv.paid_at,
    ) for inv in invoices]


@router.put("/admin/customers/{user_id}", response_model=AdminCustomerOut)
def update_customer(
    user_id: int,
    req: AdminCustomerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    تعديل بيانات عميل من لوحة الأدمن — الاسم، البريد، العمر، الجنس،
    الحساسيات، الملاحظات الصحية، وحالة تفعيل الحساب. تحديث جزئي
    (الحقول غير المُرسَلة لا تتغيّر).
    """
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id, User.role == UserRole.CUSTOMER).first()
    if not user:
        raise HTTPException(404, "Customer not found")

    for field, val in req.model_dump(exclude_unset=True).items():
        if field == "allergies" and isinstance(val, list):
            val = json.dumps(val)
        setattr(user, field, val)
    db.commit()
    db.refresh(user)
    audit("admin_customer_update", current_user.id, get_client_ip(request),
          f"Admin updated customer {user_id} ({user.email})")
    return _to_admin_out(user, db)


@router.post("/admin/customers/{user_id}/reset-password")
def reset_customer_password(
    user_id: int,
    req: AdminPasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    تعيين كلمة مرور جديدة لعميل من لوحة الأدمن.
    لأسباب أمنية لا تُخزَّن كلمات المرور بنص صريح ولا يمكن استرجاع القيمة
    الحالية أبداً (bcrypt hash فقط) — لذلك هذا endpoint يُنشئ كلمة مرور
    جديدة بدل عرض/تعديل القديمة.
    """
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id, User.role == UserRole.CUSTOMER).first()
    if not user:
        raise HTTPException(404, "Customer not found")

    user.password_hash = hash_password(req.new_password)
    db.commit()
    audit("admin_password_reset", current_user.id, get_client_ip(request),
          f"Admin reset password for customer {user_id} ({user.email})")
    return {"message": "Password updated"}