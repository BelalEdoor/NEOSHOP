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
    AWAITING_REFILL     = "AWAITING_REFILL"
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
    AWAITING_REFILL = "AWAITING_REFILL"
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
    BRAKE_RELEASED      = "BRAKE_RELEASED"
    PROLONGED_HOLDING   = "PROLONGED_HOLDING"
    UNSCANNED_IN_CART   = "UNSCANNED_IN_CART"
    PLEASE_SCAN_PRODUCT = "PLEASE_SCAN_PRODUCT"
    PRODUCT_NOT_SCANNED = "PRODUCT_NOT_SCANNED"


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
    recommendations_enabled: bool   = True
    onboarding_completed:    bool   = False
    other_health_notes: Optional[str] = None
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name:      Optional[str]       = None
    email:     Optional[EmailStr]  = None
    allergies: Optional[List[str]] = None
    age:       Optional[int]       = None
    gender:    Optional[str]       = None
    recommendations_enabled: Optional[bool] = None
    onboarding_completed:    Optional[bool] = None
    other_health_notes: Optional[str] = None


# ─── Admin — Customer Accounts (صفحة "حسابات العملاء" بالسايدبار) ──────────────
class AdminCustomerOut(UserOut):
    """نفس UserOut + إحصاءات سريعة تُعرض بجدول لوحة الأدمن."""
    total_orders: int   = 0
    total_spent:  float = 0.0

class AdminCustomerUpdate(BaseModel):
    """تعديل بيانات عميل من لوحة الأدمن — كل الحقول اختيارية (تحديث جزئي)."""
    name:      Optional[str]       = None
    email:     Optional[EmailStr]  = None
    age:       Optional[int]       = None
    gender:    Optional[str]       = None
    allergies: Optional[List[str]] = None
    other_health_notes: Optional[str] = None
    is_active: Optional[bool]      = None

class AdminPasswordReset(BaseModel):
    """
    تعيين كلمة مرور جديدة لعميل من لوحة الأدمن.
    ملاحظة أمان: كلمات المرور تُخزَّن مُجزَّأة (bcrypt) ولا يمكن استرجاع أو
    عرض القيمة الأصلية أبداً — لذلك لوحة الأدمن توفر "تعيين كلمة مرور جديدة"
    فقط، وليس عرض/تعديل الكلمة الحالية.
    """
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _min_len(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v



# ─── Product ───────────────────────────────────────────────────────────────────
class ProductOut(BaseModel):
    id:          int
    name:        str
    name_ar:     Optional[str]       = None
    price:       float
    barcode:     Optional[str]       = None
    quantity:    int
    category:    Optional[str]       = None
    # فئة موديل الرؤية الحاسوبية (bottle/candy/chips/chocolate/nuts/pasta) —
    # None يعني هذا المنتج غير مغطّى بكشف السرقة البصري.
    cv_category: Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = []
    allergens:   Optional[List[str]] = []
    image_url:   Optional[str]       = None
    location_x:  int                 = 0
    location_y:  int                 = 0
    section:     Optional[str]       = None
    is_on_offer:    bool             = False
    old_price:      Optional[float]  = None
    offer_expires_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name:        str
    name_ar:     Optional[str]       = None
    price:       float
    barcode:     Optional[str]       = None
    quantity:    int                 = 0
    category:    Optional[str]       = None
    cv_category: Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = []
    allergens:   Optional[List[str]] = []
    image_url:   Optional[str]       = None
    section:     Optional[str]       = None
    is_on_offer:    bool             = False
    old_price:      Optional[float]  = None
    offer_expires_at: Optional[datetime] = None

class ProductUpdate(BaseModel):
    name:        Optional[str]       = None
    name_ar:     Optional[str]       = None
    price:       Optional[float]     = None
    barcode:     Optional[str]       = None
    quantity:    Optional[int]       = None
    category:    Optional[str]       = None
    cv_category: Optional[str]       = None
    brand:       Optional[str]       = None
    description: Optional[str]       = None
    ingredients: Optional[List[str]] = None
    allergens:   Optional[List[str]] = None
    image_url:   Optional[str]       = None
    section:     Optional[str]       = None
    is_on_offer:    Optional[bool]   = None
    old_price:      Optional[float]  = None
    offer_expires_at: Optional[datetime] = None


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
    pending_change: float = 0.0
    method:         str
    status:         str
    started_at:     Optional[datetime] = None
    completed_at:   Optional[datetime] = None
    class Config:
        from_attributes = True

class RefillAlertOut(BaseModel):
    """تنبيه نفاد أنابيب العملات — يُعرض بلوحة الأدمن."""
    payment_id:       int
    invoice_id:       Optional[int] = None
    invoice_code:     Optional[str] = None
    session_id:       Optional[int] = None
    cart_rfid:        Optional[str] = None
    remaining_change: float
    device_id:        Optional[str] = None
    started_at:       Optional[datetime] = None
    class Config:
        from_attributes = True

class RefillNotificationOut(BaseModel):
    """صف واحد بصفحة (الإشعارات) — تنبيه نفاد أنابيب، نشط أو محلول."""
    payment_id:       int
    invoice_code:     Optional[str] = None
    device_id:        Optional[str] = None
    remaining_change: float
    status:           str  # "pending" | "resolved"
    requested_at:     Optional[datetime] = None
    resolved_at:      Optional[datetime] = None
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

class HealthConditionSelection(BaseModel):
    condition_id: int
    severity:     str = "moderate"  # 'mild' | 'moderate' | 'severe'

class OnboardingRequest(BaseModel):
    """What the onboarding page submits: checked allergy names (matching the
    same string format User.allergies already uses) and selected health
    condition IDs with severity, plus an optional free-text note."""
    allergies:        List[str] = []
    health_conditions: List[HealthConditionSelection] = []
    other_notes:      Optional[str] = None


# ─── WebSocket Messages ────────────────────────────────────────────────────────
class WSMessage(BaseModel):
    type:    str
    data:    Optional[Any] = None
    session_id: Optional[int] = None


TokenResponse.model_rebuild()