"""
routers/auth.py
===============
Authentication — تسجيل الدخول والتسجيل.
عند تسجيل الدخول بنجاح تُنشأ Shopping Session جديدة تلقائياً.
نُقل من الباك اند القديم مع إضافة إنشاء الجلسة.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import (
    hash_password, verify_password, create_access_token,
    validate_email, validate_password, sanitize_string,
    check_rate_limit, get_client_ip, audit,
)
from models.user import User, UserRole
from schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
import json

router = APIRouter()


def _to_user_out(user: User) -> UserOut:
    allergies = []
    if user.allergies:
        try:
            allergies = json.loads(user.allergies)
        except Exception:
            allergies = [a.strip() for a in user.allergies.split(",") if a.strip()]
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        allergies=allergies,
        age=user.age,
        gender=user.gender,
        is_active=user.is_active,
        created_at=user.created_at,
        recommendations_enabled=user.recommendations_enabled,
        onboarding_completed=user.onboarding_completed,
        other_health_notes=user.other_health_notes,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    check_rate_limit(ip, "register")

    email = validate_email(req.email)
    validate_password(req.password)
    name = sanitize_string(req.name or "", max_len=100)
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(req.password),
        role=UserRole(req.role) if req.role else UserRole.CUSTOMER,
        allergies=json.dumps([]),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit("register", user.id, ip, f"New user: {email}")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=_to_user_out(user))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    check_rate_limit(ip, "login")

    email = validate_email(req.email)
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(req.password, user.password_hash):
        audit("login_fail", None, ip, f"Failed login: {email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    audit("login", user.id, ip, f"Successful login: {email}")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=_to_user_out(user))
