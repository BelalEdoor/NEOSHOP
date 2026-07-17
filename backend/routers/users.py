"""
routers/users.py — إدارة بيانات المستخدمين
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user, get_client_ip, audit, ADMIN_EMAILS
from models.user import User
from schemas import UserOut, UserUpdate
import json

router = APIRouter()


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