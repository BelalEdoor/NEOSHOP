from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user

from models.user import User
from models.product import Product

from recommendation.analyze_product import analyze_product

router = APIRouter()


@router.get("/{product_id}")
def recommend_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    result = analyze_product(
        db=db,
        user_id=current_user.id,
        product={
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "subcategory": getattr(product, "subcategory", None),
            "brand": product.brand,
            "description": product.description,
            "ingredients": product.ingredients,
            "allergens": product.allergens,
        },
    )

    return result