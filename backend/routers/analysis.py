"""
routers/analysis.py
====================
Analysis router - AI-powered allergen + health-condition detection.

تغيير مهم عن النسخة السابقة:
  - المطابقة الآن تتم عبر الجداول المنظَّمة (Allergen, ProductAllergen,
    CustomerAllergy, HealthCondition, CustomerHealthCondition) بدلاً من
    البحث النصي بالكلمات المفتاحية (ALLERGEN_KEYWORDS) في حقول النص الحر.
  - شكل الـ API لم يتغيّر: matched_allergens تبقى List[str] بنفس الأسماء
    المستخدمة في الواجهة الأمامية (مثل "milk", "peanuts")، لذلك لا حاجة
    لأي تعديل في AllergenModal.jsx أو ProfilePage.jsx.
  - أُضيفت طبقة تحذير صحي جديدة (health conditions) لم تكن موجودة سابقاً:
    إذا كان المنتج يحتوي سكر/صوديوم/سعرات أعلى من الحد المسموح لحالة
    العميل الصحية، يُعاد warning بدلاً من block.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.product import Product
from models.recommendation_engine import (
    Allergen, CustomerAllergy, ProductAllergen,
    HealthCondition, CustomerHealthCondition,
)
from schemas import AnalysisRequest, AllergenResult, ProductOut, BarcodeScanlResult, OnboardingRequest, UserOut
from routers.products import _serialize as _serialize_product
import json
import os

# Categories considered food. Used to skip the allergen/health-condition
# engine entirely for non-food items (cleaning supplies, electronics, etc.)
# where an allergen check is meaningless. Add new food categories here as
# the catalog grows -- this is intentionally a simple allow-list rather
# than an is_food column, since category already exists on every product
# and the team's catalog is organized by category already.
FOOD_CATEGORIES = {
    "dairy", "bakery", "snacks", "beverages", "produce",
    "meat", "pantry", "frozen", "deli", "seafood",
}


def _is_food_product(product: Product) -> bool:
    return (product.category or "").strip().lower() in FOOD_CATEGORIES


router = APIRouter()

AI_BACKEND_URL = os.getenv("AI_BACKEND_URL", "http://localhost:8000")
AI_TIMEOUT = 12.0

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# Maps HealthCondition.related_nutrient values to actual Product columns.
# Kept as an explicit dict (not getattr on a raw string) so a bad/unexpected
# value in the database can never reach into an unrelated model attribute.
NUTRIENT_TO_COLUMN = {
    "sugar": "sugar_g",
    "sodium": "sodium_mg",
    "calories": "calories",
}


# ── Allergen matching (normalized tables, replaces keyword scanning) ──────────

def _get_user_allergy_names(db: Session, user: User) -> List[str]:
    """
    Source of truth for 'what is this user allergic to' stays
    User.allergies (JSON list of strings) — unchanged, so registration
    and ProfilePage.jsx keep working exactly as before.
    """
    try:
        return json.loads(user.allergies or "[]")
    except Exception:
        return []


def _sync_user_allergies_to_normalized(db: Session, user: User, allergy_names: List[str]) -> None:
    """
    Ensures CustomerAllergy rows match what's in User.allergies right now.
    Called before any check so the normalized tables never drift out of
    sync with the JSON field the frontend actually edits.
    Unknown names (not in the Allergen table) are skipped, not errored —
    a typo'd custom allergy the user typed in ProfilePage's free-text
    input should not crash the allergen check.
    """
    matching_allergens = (
        db.query(Allergen).filter(Allergen.name.in_([n.lower() for n in allergy_names])).all()
    )
    matching_ids = {a.id for a in matching_allergens}

    existing = db.query(CustomerAllergy).filter(CustomerAllergy.user_id == user.id).all()
    existing_ids = {e.allergen_id for e in existing}

    for to_remove in existing_ids - matching_ids:
        db.query(CustomerAllergy).filter_by(user_id=user.id, allergen_id=to_remove).delete()
    for to_add in matching_ids - existing_ids:
        db.add(CustomerAllergy(user_id=user.id, allergen_id=to_add))
    db.commit()


def _check_allergens(db: Session, product: Product, user_allergy_names: List[str]) -> dict:
    """
    Returns {"matched": [...names...], "is_safe": bool}.
    Matching now goes through ProductAllergen (normalized), falling back
    to the old free-text Product.allergens field only for products that
    haven't been tagged in the new table yet — keeps existing seeded
    products usable while the catalog is migrated gradually.
    """
    if not user_allergy_names:
        return {"matched": [], "is_safe": True}

    tagged = (
        db.query(ProductAllergen, Allergen)
        .join(Allergen, ProductAllergen.allergen_id == Allergen.id)
        .filter(ProductAllergen.product_id == product.id)
        .all()
    )

    if tagged:
        product_allergen_names = {a.name for _, a in tagged}
        matched = [n for n in user_allergy_names if n.lower() in product_allergen_names]
        return {"matched": matched, "is_safe": len(matched) == 0}

    # Fallback: product not yet tagged in product_allergens — use the
    # original free-text field so untagged catalog items still get checked.
    text = (product.allergens or "").lower()
    matched = [n for n in user_allergy_names if n.lower() in text]
    return {"matched": matched, "is_safe": len(matched) == 0}


# ── Health condition matching (new) ───────────────────────────────────────────

def _check_health_conditions(db: Session, user: User, product: Product) -> Optional[str]:
    """
    Returns a human-readable reason string if the product exceeds a
    threshold tied to one of the user's recorded health conditions,
    otherwise None. New capability — there was no equivalent before.
    """
    conditions = (
        db.query(CustomerHealthCondition, HealthCondition)
        .join(HealthCondition, CustomerHealthCondition.condition_id == HealthCondition.id)
        .filter(CustomerHealthCondition.user_id == user.id)
        .all()
    )

    for _, condition in conditions:
        column_name = NUTRIENT_TO_COLUMN.get(condition.related_nutrient)
        if not column_name or condition.warning_threshold is None:
            continue
        product_value = getattr(product, column_name, None)
        if product_value is None:
            continue
        if Decimal(str(product_value)) > condition.warning_threshold:
            return f"{condition.name}: high {condition.related_nutrient}"

    return None


def _find_safe_alternatives(
    db: Session, product: Product, user_allergy_names: List[str], user: User
) -> List[Product]:
    candidates = db.query(Product).filter(
        Product.id != product.id,
        Product.category == product.category,
    ).limit(30).all()

    safe = []
    for candidate in candidates:
        if not _check_allergens(db, candidate, user_allergy_names)["is_safe"]:
            continue
        if _check_health_conditions(db, user, candidate) is not None:
            continue
        safe.append(candidate)
        if len(safe) >= 3:
            break
    return safe


async def _call_ai_backend(product_name: str, user_allergies: List[str]) -> Optional[dict]:
    if not HTTPX_AVAILABLE:
        return None
    try:
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            resp = await client.post(
                f"{AI_BACKEND_URL}/analyze",
                json={"query": product_name, "user_allergies": user_allergies, "detailed_analysis": False},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"⚠️  AllerPredict AI unavailable: {e}")
    return None


# ── Endpoints (same routes/response shapes as before) ─────────────────────────

@router.post("/check", response_model=AllergenResult)
def check_product(
    req: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if not _is_food_product(product):
        return AllergenResult(is_safe=True, matched_allergens=[], warning_message=None, suggestions=[])

    if not current_user.recommendations_enabled:
        return AllergenResult(is_safe=True, matched_allergens=[], warning_message=None, suggestions=[])

    allergy_names = req.user_allergies if req.user_allergies is not None else _get_user_allergy_names(db, current_user)
    if allergy_names:
        _sync_user_allergies_to_normalized(db, current_user, allergy_names)

    allergen_check = _check_allergens(db, product, allergy_names)
    condition_warning = None if not allergen_check["is_safe"] else _check_health_conditions(db, current_user, product)

    is_safe = allergen_check["is_safe"] and condition_warning is None
    suggestions = []
    if not is_safe:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergy_names, current_user)]

    warning_message = None
    if not allergen_check["is_safe"]:
        warning_message = f"⚠️ يحتوي هذا المنتج على: {', '.join(allergen_check['matched'])}"
    elif condition_warning:
        warning_message = f"⚠️ {condition_warning}"

    return AllergenResult(
        is_safe=is_safe,
        matched_allergens=allergen_check["matched"],
        warning_message=warning_message,
        suggestions=suggestions,
    )


@router.post("/onboarding", response_model=UserOut)
def submit_onboarding(
    req: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Called once, right after registration (or skipped). Writes:
      - allergies -> User.allergies (same JSON field ProfilePage already uses)
      - health_conditions -> CustomerHealthCondition rows (new table)
      - other_notes -> User.other_health_notes (free text, never auto-matched)
    Then marks onboarding_completed so the screen doesn't reappear.
    """
    current_user.allergies = json.dumps(req.allergies)
    current_user.other_health_notes = req.other_notes
    current_user.onboarding_completed = True

    db.query(CustomerHealthCondition).filter(CustomerHealthCondition.user_id == current_user.id).delete()
    valid_condition_ids = {c.id for c in db.query(HealthCondition.id).all()}
    for selection in req.health_conditions:
        if selection.condition_id not in valid_condition_ids:
            continue  # ignore stale/invalid IDs rather than failing the whole request
        db.add(CustomerHealthCondition(
            user_id=current_user.id,
            condition_id=selection.condition_id,
            severity=selection.severity,
        ))

    db.commit()
    db.refresh(current_user)

    allergies_out = []
    try:
        allergies_out = json.loads(current_user.allergies or "[]")
    except Exception:
        pass

    return UserOut(
        id=current_user.id, name=current_user.name, email=current_user.email,
        role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
        allergies=allergies_out, age=current_user.age, gender=current_user.gender,
        is_active=current_user.is_active, created_at=current_user.created_at,
        recommendations_enabled=current_user.recommendations_enabled,
        onboarding_completed=current_user.onboarding_completed,
        other_health_notes=current_user.other_health_notes,
    )


@router.get("/allergens")
def list_allergens(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the fixed allergen vocabulary, name + arabic name, for
    rendering selectable options on the onboarding/profile screens.
    Requires auth like every other endpoint here -- not public.
    """
    rows = db.query(Allergen).order_by(Allergen.name).all()
    return [{"id": a.id, "name": a.name, "name_ar": a.name_ar} for a in rows]


@router.get("/health-conditions")
def list_health_conditions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns the fixed health-condition vocabulary for onboarding/profile."""
    rows = db.query(HealthCondition).order_by(HealthCondition.name).all()
    return [{"id": c.id, "name": c.name, "name_ar": c.name_ar} for c in rows]


@router.get("/quick/{product_id}", response_model=AllergenResult)
def quick_check(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return check_product(
        AnalysisRequest(product_id=product_id),
        db=db,
        current_user=current_user,
    )


@router.post("/ai/{product_id}")
async def ai_analysis(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    allergy_names = _get_user_allergy_names(db, current_user)
    allergen_check = _check_allergens(db, product, allergy_names)
    condition_warning = None if not allergen_check["is_safe"] else _check_health_conditions(db, current_user, product)
    is_safe = allergen_check["is_safe"] and condition_warning is None

    suggestions = []
    if not is_safe:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergy_names, current_user)]

    ai_result = await _call_ai_backend(product.name, allergy_names)

    warning_message = None
    if not allergen_check["is_safe"]:
        warning_message = f"⚠️ يحتوي على: {', '.join(allergen_check['matched'])}"
    elif condition_warning:
        warning_message = f"⚠️ {condition_warning}"

    return {
        "product": _serialize_product(product),
        "allergen_check": {
            "is_safe": is_safe,
            "matched_allergens": allergen_check["matched"],
            "warning_message": warning_message,
            "suggestions": suggestions,
        },
        "ai_analysis": ai_result.get("analysis") if ai_result else None,
        "ai_available": ai_result is not None,
    }


@router.get("/barcode-scan/{barcode}")
async def scan_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"لا يوجد منتج بهذا الباركود: {barcode}")

    if not _is_food_product(product):
        return {
            "product": _serialize_product(product),
            "barcode": barcode,
            "allergen_check": {"is_safe": True, "matched_allergens": [], "warning_message": None, "suggestions": []},
            "ai_analysis": None,
            "ai_available": False,
            "is_food": False,
        }

    if not current_user.recommendations_enabled:
        return {
            "product": _serialize_product(product),
            "barcode": barcode,
            "allergen_check": {"is_safe": True, "matched_allergens": [], "warning_message": None, "suggestions": []},
            "ai_analysis": None,
            "ai_available": False,
            "is_food": True,
            "recommendations_disabled": True,
        }

    allergy_names = _get_user_allergy_names(db, current_user)
    allergen_check = _check_allergens(db, product, allergy_names)
    condition_warning = None if not allergen_check["is_safe"] else _check_health_conditions(db, current_user, product)
    is_safe = allergen_check["is_safe"] and condition_warning is None

    suggestions = []
    if not is_safe:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergy_names, current_user)]

    ai_result = await _call_ai_backend(product.name, allergy_names)

    warning_message = None
    if not allergen_check["is_safe"]:
        warning_message = f"⚠️ يحتوي على: {', '.join(allergen_check['matched'])}"
    elif condition_warning:
        warning_message = f"⚠️ {condition_warning}"

    return {
        "product": _serialize_product(product),
        "barcode": barcode,
        "allergen_check": {
            "is_safe": is_safe,
            "matched_allergens": allergen_check["matched"],
            "warning_message": warning_message,
            "suggestions": suggestions,
        },
        "ai_analysis": ai_result.get("analysis") if ai_result else None,
        "ai_available": ai_result is not None,
    }
