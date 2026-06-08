"""
routers/users.py — إدارة بيانات المستخدمين
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_current_user, get_client_ip, audit
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
