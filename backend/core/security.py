"""
core/security.py
================
نظام الأمان: JWT, Password Hashing, Rate Limiting, Audit Logging.
نُقل من الباك اند القديم مع تحديثات لدعم الهيكلية الجديدة.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import re, time, logging
from collections import defaultdict
from core.config import settings
from core.database import get_db

log = logging.getLogger("neoshop.security")

# ─── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT ──────────────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from models.user import User
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_user_ws(token: str, db: Session):
    """نسخة WebSocket من get_current_user (بدون Depends)."""
    from models.user import User
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None

# ─── Rate Limiting (in-memory) ────────────────────────────────────────────────
_rate_buckets: dict = defaultdict(lambda: {"count": 0, "reset": 0})
_RATE_LIMITS = {"login": (10, 60), "register": (5, 60), "default": (100, 60)}

def check_rate_limit(ip: str, action: str = "default"):
    limit, window = _RATE_LIMITS.get(action, _RATE_LIMITS["default"])
    key = f"{ip}:{action}"
    bucket = _rate_buckets[key]
    now = time.time()
    if now > bucket["reset"]:
        bucket["count"] = 0
        bucket["reset"] = now + window
    bucket["count"] += 1
    if bucket["count"] > limit:
        raise HTTPException(status_code=429, detail="Too many requests")

# ─── Validation ───────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

def validate_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Invalid email format")
    return email

def validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(422, "Password must be at least 6 characters")

def sanitize_string(s: str, max_len: int = 255) -> str:
    return re.sub(r"[<>\"'&;]", "", s.strip())[:max_len]

def validate_quantity(qty: int, min_qty: int = 1, max_qty: int = 999) -> int:
    if not (min_qty <= qty <= max_qty):
        raise HTTPException(422, f"Quantity must be between {min_qty} and {max_qty}")
    return qty

def verify_cart_ownership(item, current_user):
    if item is None:
        raise HTTPException(404, "Cart item not found")
    if item.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

# ─── Audit Logging ────────────────────────────────────────────────────────────
_audit_log = []
MAX_AUDIT_LOG = 1000

def audit(action: str, user_id, ip: str, detail: str = ""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "ip": ip,
        "detail": detail,
    }
    _audit_log.append(entry)
    if len(_audit_log) > MAX_AUDIT_LOG:
        _audit_log.pop(0)
    log.info(f"AUDIT [{action}] user={user_id} ip={ip} {detail}")

def get_audit_log():
    return list(reversed(_audit_log))

def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host

ADMIN_EMAILS = settings.get_admin_emails()
