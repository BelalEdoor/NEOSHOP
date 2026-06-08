"""
schemas/__init__.py
===================
جميع Pydantic schemas للـ Request/Response validation.
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ─── Enums (نسخ من النماذج للاستخدام في الـ API) ──────────────────────────────
class CartStatusEnum(str, Enum):
    ACTIVE              = "ACTIVE"
    PENDING_PAYMENT     = "PENDING_PAYMENT"
    PAYMENT_IN_PROGRESS = "PAYMENT_IN_PROGRESS"
    PAID                = "PAID"
    CANCELLED           = "CANCELLED"
    FAILED              = "FAILED"

class UserRoleEnum(str, Enum):
    CUSTOMER = "customer"
    OWNER    = "owner"
    SECURITY = "security"

class PaymentStatusEnum(str, Enum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    FAILED      = "FAILED"

class TransactionTypeEnum(str, Enum):
    COIN = "COIN"
    BILL = "BILL"

class TheftAlertTypeEnum(str, Enum):
    UNSCANNED_ITEM      = "UNSCANNED_ITEM"
    SUSPICIOUS_MOVEMENT = "SUSPICIOUS_MOVEMENT"
    ITEM_CONCEALED      = "ITEM_CONCEALED"
    MULTIPLE_ITEMS      = "MULTIPLE_ITEMS"
    BRAKE_ACTIVATED     = "BRAKE_ACTIVATED"


# ─── Auth ──────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str
    role:     Optional[UserRoleEnum] = UserRoleEnum.CUSTOMER

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         "UserOut"


# ─── User ──────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    role:       str
    allergies:  Optional[List[str]] = []
    age:        Optional[int]       = None
    gender:     Optional[str]       = None
    is_active:  bool                = True
    created_at: Optional[datetime]  = None
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name:      Optional[str]       = None
    email:     Optional[EmailStr]  = None
    allergies: Optional[List[str]] = None
    age:       Optional[int]       = None
    gender:    Optional[str]       = None


# ─── Product ───────────────────────────────────────────────────────────────────
class ProductOut(BaseModel):
    id:          int
    name:        str
    name_ar:     Optional[str]       = None
    price:       float
    barcode:     Optional[str]       = None
    quantity:    int
    category:    Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = []
    allergens:   Optional[List[str]] = []
    image_url:   Optional[str]       = None
    location_x:  int                 = 0
    location_y:  int                 = 0
    section:     Optional[str]       = None
    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name:        str
    name_ar:     Optional[str]       = None
    price:       float
    barcode:     Optional[str]       = None
    quantity:    int                 = 0
    category:    Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = []
    allergens:   Optional[List[str]] = []
    image_url:   Optional[str]       = None
    section:     Optional[str]       = None

class ProductUpdate(BaseModel):
    name:        Optional[str]       = None
    name_ar:     Optional[str]       = None
    price:       Optional[float]     = None
    barcode:     Optional[str]       = None
    quantity:    Optional[int]       = None
    category:    Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = None
    allergens:   Optional[List[str]] = None
    image_url:   Optional[str]       = None
    section:     Optional[str]       = None


# ─── Cart ──────────────────────────────────────────────────────────────────────
class CartOut(BaseModel):
    id:          int
    cart_number: str
    rfid_uid:    str
    status:      str
    class Config:
        from_attributes = True

class CartItemAdd(BaseModel):
    product_id: int
    quantity:   int = 1

class CartItemOut(BaseModel):
    id:                int
    product_id:        int
    quantity:          int
    unit_price:        float
    product:           Optional[ProductOut] = None
    is_safe:           Optional[bool]       = True
    matched_allergens: Optional[List[str]]  = []
    class Config:
        from_attributes = True

class CartItemRemove(BaseModel):
    product_id: int


# ─── Session ───────────────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    cart_rfid: Optional[str] = None

class SessionOut(BaseModel):
    id:           int
    user_id:      Optional[int]  = None
    cart_id:      Optional[int]  = None
    cart_rfid:    Optional[str]  = None
    status:       str
    total_amount: float
    discount:     float
    started_at:   Optional[datetime] = None
    ended_at:     Optional[datetime] = None
    items:        List[CartItemOut]  = []
    class Config:
        from_attributes = True

class FinishShoppingRequest(BaseModel):
    """يُرسَل عند ضغط "Finish Shopping" من الـ Frontend."""
    session_id: int


# ─── Invoice ───────────────────────────────────────────────────────────────────
class InvoiceOut(BaseModel):
    id:           int
    invoice_code: Optional[str]  = None
    session_id:   Optional[int]  = None
    cart_rfid:    Optional[str]  = None
    subtotal:     float
    discount:     float
    total_amount: float
    status:       str
    items_json:   Optional[str]  = None
    created_at:   Optional[datetime] = None
    paid_at:      Optional[datetime] = None
    class Config:
        from_attributes = True


# ─── Payment ───────────────────────────────────────────────────────────────────
class PaymentOut(BaseModel):
    id:             int
    invoice_id:     Optional[int]  = None
    total_due:      float
    amount_inserted: float
    change_returned: float
    method:         str
    status:         str
    started_at:     Optional[datetime] = None
    completed_at:   Optional[datetime] = None
    class Config:
        from_attributes = True

class CoinInsertedPayload(BaseModel):
    """يُرسَل من ESP32 عبر MQTT عند إدخال عملة."""
    cart_rfid:    str
    denomination: float
    count:        int = 1

class BillInsertedPayload(BaseModel):
    """يُرسَل من ESP32 عبر MQTT عند إدخال ورقة نقدية."""
    cart_rfid:    str
    denomination: float

class RFIDPaymentRequest(BaseModel):
    """يُرسَل من ESP32 عبر MQTT عند قراءة RFID في محطة الدفع."""
    cart_rfid: str
    event:     str = "payment_request"


# ─── Theft ─────────────────────────────────────────────────────────────────────
class TheftLogOut(BaseModel):
    id:               int
    session_id:       Optional[int]   = None
    alert_type:       str
    description:      Optional[str]   = None
    confidence_score: Optional[float] = None
    brake_activated:  bool
    resolved:         bool
    detected_at:      Optional[datetime] = None
    class Config:
        from_attributes = True

class TheftAlertCreate(BaseModel):
    session_id:       Optional[int]   = None
    alert_type:       TheftAlertTypeEnum
    description:      Optional[str]   = None
    confidence_score: Optional[float] = None
    brake_activated:  bool             = False


# ─── Analysis ──────────────────────────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    product_id:      int
    user_allergies:  Optional[List[str]] = None

class AllergenResult(BaseModel):
    is_safe:          bool
    matched_allergens: List[str]
    warning_message:  Optional[str]       = None
    suggestions:      List[ProductOut]    = []

class BarcodeScanlResult(BaseModel):
    product:    ProductOut
    is_safe:    bool
    matched_allergens: List[str]
    warning_message:   Optional[str]       = None
    suggestions:       List[ProductOut]    = []


# ─── WebSocket Messages ────────────────────────────────────────────────────────
class WSMessage(BaseModel):
    type:    str
    data:    Optional[Any] = None
    session_id: Optional[int] = None


TokenResponse.model_rebuild()
