"""
routers/products.py
===================
إدارة المنتجات — نُقل من الباك اند القديم مع تعديلات طفيفة.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from core.security import get_current_user, ADMIN_EMAILS
from models.product import Product
from models.user import User
from schemas import ProductOut, ProductCreate, ProductUpdate

router = APIRouter()


def _naive(dt):
    """
    Strips timezone info if present. SQLite stores DateTime(timezone=True)
    values without tzinfo regardless of the column declaration, while MySQL
    can return them either way depending on driver/config -- comparing a
    naive and an aware datetime raises TypeError, so every comparison in
    this file goes through this helper to normalize both sides first.
    """
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


def _serialize(product: Product) -> ProductOut:
    def split(s):
        if not s:
            return []
        try:
            import json
            return json.loads(s)
        except Exception:
            return [x.strip() for x in s.split(",") if x.strip()]

    return ProductOut(
        id=product.id,
        name=product.name,
        name_ar=product.name_ar,
        price=product.price,
        barcode=product.barcode,
        quantity=product.quantity or 0,
        category=product.category,
        brand=product.brand,
        description=product.description,
        ingredients=split(product.ingredients),
        allergens=split(product.allergens),
        image_url=product.image_url,
        location_x=product.location_x or 0,
        location_y=product.location_y or 0,
        section=product.section,
        is_on_offer=product.is_on_offer or False,
        old_price=product.old_price,
        offer_expires_at=product.offer_expires_at,
    )


@router.get("/", response_model=List[ProductOut])
def list_products(
    search:   Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Product)
    if search:
        like = f"%{search}%"
        q = q.filter(Product.name.ilike(like) | Product.name_ar.ilike(like))
    if category:
        q = q.filter(Product.category == category)
    return [_serialize(p) for p in q.offset(skip).limit(limit).all()]


@router.get("/offers", response_model=List[ProductOut])
def list_offers(db: Session = Depends(get_db)):
    """
    Real offers, replacing the previous hardcoded mock list in
    frontend/src/data/offersData.js. An offer is any product the store
    owner has flagged is_on_offer=True via the admin panel, and whose
    offer_expires_at is either unset or still in the future.
    """
    from datetime import datetime
    now = datetime.utcnow()
    q = db.query(Product).filter(Product.is_on_offer == True)
    products = q.all()
    active = [
        p for p in products
        if p.offer_expires_at is None or _naive(p.offer_expires_at) > now
    ]
    return [_serialize(p) for p in active]


@router.get("/barcode/{barcode}", response_model=ProductOut)
def get_by_barcode(barcode: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.barcode == barcode).first()
    if not p:
        raise HTTPException(404, f"Product with barcode '{barcode}' not found")
    return _serialize(p)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    return _serialize(p)


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(
    req: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    if req.barcode and db.query(Product).filter(Product.barcode == req.barcode).first():
        raise HTTPException(400, "Barcode already exists")

    import json
    p = Product(
        name=req.name, name_ar=req.name_ar, price=req.price,
        barcode=req.barcode, quantity=req.quantity, category=req.category,
        brand=req.brand, description=req.description,
        ingredients=json.dumps(req.ingredients or []),
        allergens=json.dumps(req.allergens or []),
        image_url=req.image_url, section=req.section,
        is_on_offer=req.is_on_offer, old_price=req.old_price,
        offer_expires_at=req.offer_expires_at,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _serialize(p)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    req: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")

    import json
    for field, val in req.model_dump(exclude_unset=True).items():
        if field in ("ingredients", "allergens") and isinstance(val, list):
            val = json.dumps(val)
        setattr(p, field, val)
    db.commit()
    db.refresh(p)
    return _serialize(p)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.email not in ADMIN_EMAILS:
        raise HTTPException(403, "Admin access required")

    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")
    db.delete(p)
    db.commit()
