"""
recommendation/alternative_generator.py
=======================================

Generate safe product alternatives for the scanned product.

Workflow:
1. Search products in the same category + subcategory.
2. If too few products exist, fall back to the same category.
3. Remove the scanned product.
4. Remove products containing the user's allergens.
5. Rank remaining products by similarity.
6. Return the best alternatives.
"""

from sqlalchemy.orm import Session

from models.product import Product


def similarity_score(product: dict, candidate: Product) -> int:
    """
    Calculate how similar a candidate product is to the scanned product.
    """
    score = 0

    # Same subcategory
    if (
        product.get("subcategory")
        and candidate.subcategory
        and product["subcategory"] == candidate.subcategory
    ):
        score += 60

    # Same brand
    if (
        product.get("brand")
        and candidate.brand
        and product["brand"] == candidate.brand
    ):
        score += 20

    # Similar price
    if (
        product.get("price") is not None
        and candidate.price is not None
        and abs(product["price"] - candidate.price) <= 2
    ):
        score += 10

    # Similar product name
    if (
        product.get("name")
        and candidate.name
    ):
        source_words = {
            w.lower()
            for w in product["name"].split()
            if len(w) > 2
        }

        candidate_words = {
            w.lower()
            for w in candidate.name.split()
        }

        score += len(source_words & candidate_words) * 5

    return score


def generate_safe_alternatives(
    db: Session,
    profile: dict,
    product: dict,
    top_k: int = 5,
):
    """
    Generate safe alternatives for a scanned product.
    """

    allergies = {
        allergy.lower()
        for allergy in profile.get("allergies", [])
    }

    category = product.get("category")
    subcategory = product.get("subcategory")

    # --------------------------------------------------
    # First search:
    # Same Category + Same Subcategory
    # --------------------------------------------------

    candidates = (
        db.query(Product)
        .filter(
            Product.category == category,
            Product.subcategory == subcategory,
        )
        .all()
    )

    ranked = []

    for candidate in candidates:

        # Skip scanned product
        if candidate.id == product["id"]:
            continue

        # Skip products with no stock
        if candidate.quantity is not None and candidate.quantity <= 0:
            continue

        # Skip products on the same allergy
        # ملاحظة: نتعمّد استبعاد candidate.name من نص البحث عن الحساسية —
        # لأنه اسم المنتج ("Almond Milk") ممكن يحتوي كلمة الحساسية حرفياً
        # (milk) بدون ما يكون المنتج فعلاً يحتوي عليها (بديل نباتي حقيقي).
        # نفس المنطق المستخدم بـ health_checker.py — المصدر الموثوق الوحيد
        # هو حقول ingredients/allergens الفعلية، مش اسم العرض.
        searchable = (
            f"{candidate.ingredients or ''} "
            f"{candidate.allergens or ''}"
        ).lower()

        if any(allergy in searchable for allergy in allergies):
            continue

        # Skip products with a different subcategory when enough exist
        if (
            subcategory
            and candidate.subcategory
            and candidate.subcategory != subcategory
            and len(candidates) > 5
        ):
            continue

        score = similarity_score(product, candidate)

        ranked.append({
            "score": score,
            "product": {
                "id": candidate.id,
                "barcode": candidate.barcode,
                "name": candidate.name,
                "brand": candidate.brand,
                "price": candidate.price,
                "category": candidate.category,
                "subcategory": candidate.subcategory,
                "ingredients": candidate.ingredients,
                "allergens": candidate.allergens,
                "image_url": candidate.image_url,
                # القيم الغذائية — لازمة عشان check_product_health() يقدر
                # يقيّم صحة البديل بدقّة (بدونها، القيم الناقصة بتترجم صفر
                # وبتظهر البدائل "صحية" بشكل وهمي).
                "sugar_g": candidate.sugar_g,
                "sodium_mg": candidate.sodium_mg,
                "cholesterol_mg": candidate.cholesterol_mg,
                "saturated_fat_g": candidate.saturated_fat_g,
                "calories": candidate.calories,
                "fiber_g": candidate.fiber_g,
            },
        })

    # --------------------------------------------------
    # Second pass:
    # Same Category only when we still need more results
    # --------------------------------------------------

    if len(ranked) < top_k and category:
        fallback_candidates = (
            db.query(Product)
            .filter(Product.category == category)
            .all()
        )

        for candidate in fallback_candidates:

            # Skip scanned product
            if candidate.id == product["id"]:
                continue

            # Skip products already in ranked results
            if any(item["product"]["id"] == candidate.id for item in ranked):
                continue

            # Skip products with no stock
            if candidate.quantity is not None and candidate.quantity <= 0:
                continue

            searchable = (
                f"{candidate.ingredients or ''} "
                f"{candidate.allergens or ''}"
            ).lower()

            if any(allergy in searchable for allergy in allergies):
                continue

            score = similarity_score(product, candidate)

            ranked.append({
                "score": score,
                "product": {
                    "id": candidate.id,
                    "barcode": candidate.barcode,
                    "name": candidate.name,
                    "brand": candidate.brand,
                    "price": candidate.price,
                    "category": candidate.category,
                    "subcategory": candidate.subcategory,
                    "ingredients": candidate.ingredients,
                    "allergens": candidate.allergens,
                    "image_url": candidate.image_url,
                    "sugar_g": candidate.sugar_g,
                    "sodium_mg": candidate.sodium_mg,
                    "cholesterol_mg": candidate.cholesterol_mg,
                    "saturated_fat_g": candidate.saturated_fat_g,
                    "calories": candidate.calories,
                    "fiber_g": candidate.fiber_g,
                },
            })

            if len(ranked) >= top_k:
                break

    # --------------------------------------------------
    # Third pass: whole catalog, ranked by shared name/ingredient
    # words — only when the category-restricted search above still
    # came up short.
    #
    # مهم: بعض البدائل الحقيقية الآمنة مش بنفس فئة المنتج الممسوح —
    # مثال: "Whole Milk 1L" فئته Dairy، لكن بديله النباتي الآمن
    # "Almond Milk 1L" مصنّف تحت Beverages. لو اقتصرنا البحث على نفس
    # الفئة بس، ما رح نلاقي هيك بدائل حتى لو موجودة فعلياً بالكتالوج.
    # هون منوسّع البحث لكل المنتجات ونعتمد على تشابه الاسم/المكوّنات
    # (similarity_score) لترتيب النتائج، مع نفس فلترة الحساسية والمخزون.
    # --------------------------------------------------

    if len(ranked) < top_k:
        already_ids = {item["product"]["id"] for item in ranked} | {product["id"]}

        # كلمات عامة/أوصاف عبوة ما بتحدد نوع المنتج فعلياً — تجاهلها عشان
        # ما نطابق منتجات مش مرتبطة (مثال: "Whole Milk" و"Whole Wheat Bread"
        # بتشتركوا بكلمة "Whole" بس، وهاد مش تشابه حقيقي).
        _GENERIC_WORDS = {
            "whole", "fresh", "natural", "large", "small", "medium",
            "bottle", "pack", "box", "bag", "can", "jar", "organic",
            "premium", "classic", "original", "extra", "new",
        }

        source_words = {
            w.lower() for w in (product.get("name") or "").split()
            if len(w) > 2 and w.lower() not in _GENERIC_WORDS and not any(c.isdigit() for c in w)
        }

        catalog_candidates = (
            db.query(Product)
            .filter(Product.id.notin_(already_ids))
            .all()
        )

        for candidate in catalog_candidates:
            if candidate.quantity is not None and candidate.quantity <= 0:
                continue

            searchable = (
                f"{candidate.ingredients or ''} "
                f"{candidate.allergens or ''}"
            ).lower()

            if any(allergy in searchable for allergy in allergies):
                continue

            candidate_words = {w.lower() for w in (candidate.name or "").split()}
            if not (source_words & candidate_words):
                # كلمة مشتركة "حقيقية" واحدة على الأقل بالاسم (مثلاً "Milk")
                # — مو مجرد وصف عبوة عام — حتى ما نقترح منتجات غير مرتبطة.
                continue

            score = similarity_score(product, candidate)

            ranked.append({
                "score": score,
                "product": {
                    "id": candidate.id,
                    "barcode": candidate.barcode,
                    "name": candidate.name,
                    "brand": candidate.brand,
                    "price": candidate.price,
                    "category": candidate.category,
                    "subcategory": candidate.subcategory,
                    "ingredients": candidate.ingredients,
                    "allergens": candidate.allergens,
                    "image_url": candidate.image_url,
                    "sugar_g": candidate.sugar_g,
                    "sodium_mg": candidate.sodium_mg,
                    "cholesterol_mg": candidate.cholesterol_mg,
                    "saturated_fat_g": candidate.saturated_fat_g,
                    "calories": candidate.calories,
                    "fiber_g": candidate.fiber_g,
                },
            })

            if len(ranked) >= top_k:
                break

    # --------------------------------------------------
    # Sort by similarity score
    # --------------------------------------------------

    ranked.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return [
        item["product"]
        for item in ranked[:top_k]
    ]