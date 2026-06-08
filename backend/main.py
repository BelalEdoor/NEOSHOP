"""
main.py
=======
NEOSHOP — FastAPI Backend v4.0
Distributed Smart Cart Architecture

الهيكلية:
  Raspberry Pi ←→ Backend (هذا الملف) ←→ ESP32
  الـ Backend هو Central Brain للنظام بالكامل.

عند بدء التشغيل:
  1. إنشاء جداول قاعدة البيانات
  2. تحميل نموذج YOLOv8
  3. الاتصال بـ MQTT Broker
  4. تسجيل MQTT handlers
  5. Seed البيانات الابتدائية
"""
import asyncio
import time
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import engine, Base, SessionLocal
from core.security import get_audit_log

# ─── Import all models (must be before create_all) ────────────────────────────
import models  # noqa: F401 — triggers __init__.py which imports all models

# ─── Import routers ───────────────────────────────────────────────────────────
from routers import auth, users, products, session, cart, payment
from routers import invoices, theft, analysis, admin
from websocket_router import router as ws_router, manager as ws_manager
from mqtt.client import mqtt_service
from mqtt.handlers import setup_handlers
import mqtt.handlers as mqtt_handlers
from cv.theft_detection import theft_service

log = logging.getLogger("neoshop.main")
logging.basicConfig(level=logging.INFO)


# ══════════════════════════════════════════════════════════════════════════════
# Application Lifespan
# ══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """يُنفَّذ عند بدء وإيقاف التطبيق."""
    log.info("🚀 NEOSHOP Backend starting...")

    # 1. إنشاء جداول قاعدة البيانات
    Base.metadata.create_all(bind=engine)
    log.info("✓ Database tables created")

    # 2. تحميل YOLOv8
    theft_service.load_model()
    log.info("✓ YOLOv8 model loaded")

    # 3. تهيئة MQTT
    loop = asyncio.get_event_loop()
    mqtt_service.setup(loop)
    mqtt_handlers.ws_manager = ws_manager  # حقن WebSocket manager
    setup_handlers()
    log.info("✓ MQTT service initialized")

    # 4. Seed البيانات الابتدائية
    _auto_seed()
    log.info("✓ Database seeded")

    log.info("✅ NEOSHOP Backend ready!")

    yield  # التطبيق يعمل هنا

    log.info("🛑 NEOSHOP Backend shutting down...")


def _auto_seed():
    """تهيئة البيانات الابتدائية إذا كانت قاعدة البيانات فارغة."""
    db = SessionLocal()
    try:
        from models.user import User, UserRole
        from core.security import hash_password
        import json

        # إنشاء مستخدم Admin إذا لم يكن موجوداً
        if not db.query(User).filter(User.email == "admin@neoshop.com").first():
            db.add(User(
                name="Admin Owner",
                email="admin@neoshop.com",
                password_hash=hash_password("admin1234"),
                role=UserRole.OWNER,
                allergies=json.dumps([]),
            ))
            db.commit()
            log.info("✓ Admin user created (admin@neoshop.com / admin1234)")

        # إنشاء مستخدم موظف أمن
        if not db.query(User).filter(User.email == "security@neoshop.com").first():
            db.add(User(
                name="Security Officer",
                email="security@neoshop.com",
                password_hash=hash_password("security1234"),
                role=UserRole.SECURITY,
                allergies=json.dumps([]),
            ))
            db.commit()

        # إنشاء عربة افتراضية
        from models.cart import Cart
        if db.query(Cart).count() == 0:
            db.add(Cart(cart_number="CART-001", rfid_uid="RFID-DEFAULT-001"))
            db.add(Cart(cart_number="CART-002", rfid_uid="RFID-DEFAULT-002"))
            db.commit()
            log.info("✓ Default carts created")

        # Seed المنتجات من ملف seed القديم
        from models.product import Product
        if db.query(Product).count() == 0:
            try:
                import sys
                sys.path.insert(0, os.path.dirname(__file__))
                import seed as s
                s.seed_products_only(db)
                log.info("✓ Products seeded")
            except Exception as e:
                log.warning(f"Could not seed products: {e}")

    except Exception as e:
        log.warning(f"Seed warning: {e}")
        db.rollback()
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="NEOSHOP Distributed Backend v4.0",
    description="""
    Central Brain للنظام الموزّع:
    - Raspberry Pi ← Frontend + Barcode Scanner + Camera
    - ESP32 ← Payment Station (RFID + Coin + Bill)
    - Laptop Backend ← AI + Computer Vision + MQTT + Database
    """,
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]        = "SAMEORIGIN"
    response.headers["X-XSS-Protection"]       = "1; mode=block"
    return response

@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    t = time.time()
    r = await call_next(request)
    r.headers["X-Process-Time"] = f"{(time.time()-t)*1000:.1f}ms"
    return r

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ─── API Routes ───────────────────────────────────────────────────────────────
# Auth
app.include_router(auth.router,      prefix="/api/auth",     tags=["Auth"])
app.include_router(users.router,     prefix="/api/users",    tags=["Users"])

# Shopping
app.include_router(products.router,  prefix="/api/products", tags=["Products"])
app.include_router(session.router,   prefix="/api/sessions", tags=["Sessions"])
app.include_router(cart.router,      prefix="/api/carts",    tags=["Carts"])

# Payment
app.include_router(payment.router,   prefix="/api/payments", tags=["Payments"])
app.include_router(invoices.router,  prefix="/api/invoices", tags=["Invoices"])

# Security
app.include_router(theft.router,     prefix="/api/theft",    tags=["Theft Detection"])

# Analysis (AI)
app.include_router(analysis.router,  prefix="/api/analysis", tags=["AI Analysis"])

# Admin Dashboard
app.include_router(admin.router,     prefix="/api/admin",    tags=["Admin"])

# WebSocket
app.include_router(ws_router, tags=["WebSocket"])

# ─── Utility Endpoints ────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "ok",
        "system": "NEOSHOP Distributed Backend",
        "version": "4.0.0",
        "architecture": {
            "raspberry_pi": "Frontend + Barcode + Camera",
            "esp32":        "Payment Station (RFID + Cash)",
            "backend":      "AI + CV + MQTT + Database (this server)",
        },
    }

@app.get("/health", tags=["Health"])
def health():
    return {
        "status":      "healthy",
        "ts":          time.time(),
        "mqtt":        mqtt_service.is_connected,
        "yolo_ready":  theft_service.is_ready,
    }

@app.get("/api/audit", tags=["Admin"])
def get_audit(current_user=None):
    return get_audit_log()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.ENV == "production":
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    raise exc
