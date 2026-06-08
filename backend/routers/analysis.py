"""Analysis router - AI-powered allergen detection + AllerPredict AI integration"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.product import Product
from schemas import AnalysisRequest, AllergenResult, ProductOut, BarcodeScanlResult
from routers.products import _serialize as _serialize_product
import json
import os

router = APIRouter()

AI_BACKEND_URL = os.getenv("AI_BACKEND_URL", "http://localhost:8000")
AI_TIMEOUT = 12.0

# FIX 5: httpx is optional — app still works without AI backend
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

ALLERGEN_KEYWORDS = {
    "milk":      ["milk", "dairy", "lactose", "cream", "butter", "cheese", "whey", "casein"],
    "nuts":      ["nuts", "nut", "almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut", "macadamia"],
    "peanuts":   ["peanut", "groundnut", "arachis"],
    "gluten":    ["gluten", "wheat", "barley", "rye", "oats", "spelt", "semolina", "flour"],
    "eggs":      ["egg", "albumin", "mayonnaise", "meringue"],
    "soy":       ["soy", "soya", "tofu", "edamame", "tempeh"],
    "fish":      ["fish", "salmon", "tuna", "cod", "anchovy", "sardine", "bass", "tilapia"],
    "shellfish": ["shellfish", "shrimp", "prawn", "crab", "lobster", "oyster", "clam", "scallop"],
    "sesame":    ["sesame", "tahini"],
    "sulfites":  ["sulfite", "sulphite", "sulfur dioxide"],
}


def _check_allergens(product: Product, user_allergies: List[str]) -> dict:
    if not product.ingredients and not product.allergens:
        return {"matched": [], "is_safe": True}

    combined_text = (
        (product.ingredients or "") + " " + (product.allergens or "")
    ).lower()

    matched = []
    for ua in user_allergies:
        ua_lower = ua.lower().strip()
        if ua_lower in combined_text:
            matched.append(ua)
            continue
        for canonical, keywords in ALLERGEN_KEYWORDS.items():
            if ua_lower in keywords or ua_lower == canonical:
                if any(kw in combined_text for kw in keywords):
                    matched.append(ua)
                    break

    return {"matched": list(set(matched)), "is_safe": len(matched) == 0}


def _find_safe_alternatives(db: Session, product: Product, user_allergies: List[str]) -> List[Product]:
    candidates = db.query(Product).filter(
        Product.id != product.id,
        Product.category == product.category,
    ).limit(30).all()

    safe = []
    for candidate in candidates:
        if _check_allergens(candidate, user_allergies)["is_safe"]:
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


def _get_user_allergies(current_user: User) -> List[str]:
    try:
        return json.loads(current_user.allergies or "[]")
    except Exception:
        return []


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/check", response_model=AllergenResult)
def check_product(
    req: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    allergies = req.user_allergies if req.user_allergies is not None else _get_user_allergies(current_user)
    if not allergies:
        return AllergenResult(is_safe=True, matched_allergens=[], warning_message=None, suggestions=[])

    check = _check_allergens(product, allergies)
    suggestions = []
    if not check["is_safe"]:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergies)]

    return AllergenResult(
        is_safe=check["is_safe"],
        matched_allergens=check["matched"],
        warning_message=(
            f"⚠️ يحتوي هذا المنتج على: {', '.join(check['matched'])}"
            if not check["is_safe"] else None
        ),
        suggestions=suggestions,
    )


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

    allergies = _get_user_allergies(current_user)
    check = _check_allergens(product, allergies)
    suggestions = []
    if not check["is_safe"]:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergies)]

    ai_result = await _call_ai_backend(product.name, allergies)

    return {
        "product": _serialize_product(product),
        "allergen_check": {
            "is_safe": check["is_safe"],
            "matched_allergens": check["matched"],
            "warning_message": (
                f"⚠️ يحتوي على: {', '.join(check['matched'])}" if not check["is_safe"] else None
            ),
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

    allergies = _get_user_allergies(current_user)
    check = _check_allergens(product, allergies)
    suggestions = []
    if not check["is_safe"]:
        suggestions = [_serialize_product(p) for p in _find_safe_alternatives(db, product, allergies)]

    ai_result = await _call_ai_backend(product.name, allergies)

    return {
        "product": _serialize_product(product),
        "barcode": barcode,
        "allergen_check": {
            "is_safe": check["is_safe"],
            "matched_allergens": check["matched"],
            "warning_message": (
                f"⚠️ يحتوي على: {', '.join(check['matched'])}" if not check["is_safe"] else None
            ),
            "suggestions": suggestions,
        },
        "ai_analysis": ai_result.get("analysis") if ai_result else None,
        "ai_available": ai_result is not None,
    }
