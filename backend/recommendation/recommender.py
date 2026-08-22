import pickle

import numpy as np

from recommendation.filters import (
    remove_same_product,
    remove_duplicate_names,
    filter_allergies,
    filter_health,
    diversify_categories,
)

# ─── Lazy imports (مهم جداً) ────────────────────────────────────────────────
# faiss و sentence-transformers (وبداخلها torch) ما بينستوردوا هون بأعلى
# الملف عمداً. الاستيراد على مستوى الوحدة (module-level import) بينفّذ فوراً
# لما main.py يستورد الراوترات وقت إقلاع السيرفر — يعني faiss/torch (نسخة
# ثانية) بتتحمّل بنفس لحظة تحميل cv/ (اللي أصلاً فيها torch + opencv +
# mediapipe). تحميل كل هالمكتبات الـ native الثقيلة مع بعض بنفس اللحظة هو
# سبب شائع لـ segmentation fault على macOS (تعارض OpenMP/BLAS بين النسخ).
#
# بدل هيك، بنستورد faiss و SentenceTransformer فقط داخل _get_index() /
# _get_model() — أي أول مرة فعلية حدا يستخدم فيها endpoint من
# /api/recommendations أو /api/ai/recommendations. هيك باقي المشروع
# (المتجر، الكاشير، الكاميرا) بيشتغل ويقلع طبيعي 100% حتى لو صار تعارض
# بمكتبات نظام التوصيات — الكراش (لو صار) بيصير بس وقت أول استدعاء API
# للتوصيات، مش وقت إقلاع السيرفر كله.
faiss = None
SentenceTransformer = None


def _ensure_faiss():
    global faiss
    if faiss is None:
        try:
            import faiss as _faiss
            faiss = _faiss
        except ImportError:  # pragma: no cover - depends on local environment
            raise ImportError("faiss is required to generate recommendations")
    return faiss


def _ensure_sentence_transformer():
    global SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as _ST
            SentenceTransformer = _ST
        except ImportError:  # pragma: no cover - depends on local environment
            raise ImportError("sentence-transformers is required to generate recommendations")
    return SentenceTransformer


_MODEL = None
_INDEX = None
_PRODUCTS = None

_HEALTHY_KEYWORDS = (
    "organic",
    "natural",
    "whole",
    "fresh",
    "fruit",
    "vegetable",
    "unsweetened",
    "low sugar",
)
_UNHEALTHY_KEYWORDS = (
    "sugar",
    "sweet",
    "chocolate",
    "candy",
    "fried",
    "processed",
    "artificial",
    "cream",
    "flavor",
)
_SIMILARITY_WEIGHT = 0.40
_HEALTH_WEIGHT = 0.35
_PREFERENCE_WEIGHT = 0.20
_METADATA_WEIGHT = 0.05


def to_python(value):
    if value is None:
        return None

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    return value


def _get_model():
    global _MODEL

    ST = _ensure_sentence_transformer()

    if _MODEL is None:
        _MODEL = ST("sentence-transformers/all-MiniLM-L6-v2")

    return _MODEL


def _get_index():
    global _INDEX

    fa = _ensure_faiss()

    if _INDEX is None:
        _INDEX = fa.read_index("products.index")

    return _INDEX


def _get_products():
    global _PRODUCTS

    if _PRODUCTS is None:
        with open("products.pkl", "rb") as f:
            _PRODUCTS = pickle.load(f)

    return _PRODUCTS


def compute_final_score(similarity, health_score, preference_score, metadata_score):
    return round(
        similarity * _SIMILARITY_WEIGHT
        + health_score * _HEALTH_WEIGHT
        + preference_score * _PREFERENCE_WEIGHT
        + metadata_score * _METADATA_WEIGHT,
        6,
    )


def _compute_health_score(product):
    text = " ".join(
        [
            str(product.get("name", "")),
            str(product.get("category", "")),
            str(product.get("ingredients", "")),
        ]
    ).lower()

    if any(keyword in text for keyword in _HEALTHY_KEYWORDS):
        return 0.9
    if any(keyword in text for keyword in _UNHEALTHY_KEYWORDS):
        return 0.35
    return 0.6


def _compute_preference_score(product_text, product):
    query_tokens = {
        token for token in str(product_text).lower().replace("-", " ").split() if token
    }
    product_tokens = {
        token for token in " ".join(
            [
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("ingredients", "")),
                str(product.get("allergens", "")),
            ]
        ).lower().replace("-", " ").split() if token
    }

    if not query_tokens:
        return 0.0

    overlap = len(query_tokens & product_tokens)
    return round(overlap / max(1, len(query_tokens)), 6)


def _compute_metadata_score(product):
    score = 0.0

    if str(product.get("name", "")).strip():
        score += 0.4
    if str(product.get("category", "")).strip():
        score += 0.2
    if str(product.get("ingredients", "")).strip():
        score += 0.2
    if str(product.get("allergens", "")).strip():
        score += 0.2

    return round(min(1.0, score), 6)


def _generate_recommendation_reasons(product_text, product):
    reasons = []

    query = str(product_text).lower()

    name = str(product.get("name", "")).lower()
    category = str(product.get("category", "")).lower()
    ingredients = str(product.get("ingredients", "")).lower()

    # Product is similar to something the user previously purchased
    if name and any(word in query for word in name.split()):
        reasons.append("Similar to products you've purchased")

    # Same preferred category
    if category and category in query:
        reasons.append("Matches your preferred category")

    # Similar ingredients
    ingredient_list = [
        item.strip()
        for item in ingredients.replace(",", " ").split()
        if item.strip()
    ]

    if any(item in query for item in ingredient_list):
        reasons.append(
            "Contains ingredients similar to products you've purchased"
        )

    # Fallback reason
    if not reasons:
        reasons.append("Matches your shopping preferences")

    return reasons


def recommend(
    product_id,
    product_text,
    profile=None,
    top_k=20,
):
    user_allergies = {
        a.lower()
        for a in (profile.get("allergies", []) if profile else [])
    }

    health_conditions = {
        h.lower()
        for h in (profile.get("health_conditions", []) if profile else [])
    }

    query_embedding = _get_model().encode([product_text])
    # Retrieve a larger pool than the final result count so the ranking can be refined.
    candidate_count = max(top_k * 10, 50)

    distances, indices = _get_index().search(query_embedding, candidate_count)
    products = _get_products()

    results = []

    for distance, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue

        product = products.iloc[idx]
        product_id_value = int(product["id"])

        product_text = " ".join([
            str(product.get("name") or ""),
            str(product.get("category") or ""),
            str(product.get("subcategory") or ""),
            str(product.get("brand") or ""),
            str(product.get("ingredients") or ""),
            str(product.get("allergens") or ""),
        ])

        # Don't recommend the scanned product
        if product_id is not None and product_id_value == product_id:
            continue

        text = (
            f"{product.get('name','')} "
            f"{product.get('ingredients','')} "
            f"{product.get('allergens','')}"
        ).lower()

        if any(a in text for a in user_allergies):
            continue

        if (
            "hypertension" in health_conditions
            and product.get("sodium_mg", 0) > 400
        ):
            continue

        if (
            "diabetes" in health_conditions
            and product.get("sugar_g", 0) > 15
        ):
            continue

        if (
            "obesity" in health_conditions
            and product.get("calories", 0) > 300
        ):
            continue

        similarity = 1 / (1 + float(distance))
        health_score = _compute_health_score(product)
        preference_score = _compute_preference_score(product_text, product)
        metadata_score = _compute_metadata_score(product)
        reasons = _generate_recommendation_reasons(
            product_text,
            product
        )
        final_score = compute_final_score(
            similarity,
            health_score,
            preference_score,
            metadata_score,
        )
        match_percentage = round(final_score * 100)

        candidate = {
            "id": int(product.get("id", product_id_value)),
            "barcode": to_python(product.get("barcode")),
            "name": to_python(product.get("name")),
            "name_ar": to_python(product.get("name_ar")),
            "brand": to_python(product.get("brand")),
            "price": float(product.get("price", 0) or 0),

            "quantity": to_python(product.get("quantity")),

            "category": to_python(product.get("category")),
            "subcategory": to_python(product.get("subcategory")),
            "ingredients": to_python(product.get("ingredients")),
            "allergens": to_python(product.get("allergens")),
            "section": to_python(product.get("section")),

            "location_x": to_python(product.get("location_x")),
            "location_y": to_python(product.get("location_y")),

            "sugar_g": to_python(product.get("sugar_g")),
            "sodium_mg": to_python(product.get("sodium_mg")),
            "cholesterol_mg": to_python(product.get("cholesterol_mg")),
            "saturated_fat_g": to_python(product.get("saturated_fat_g")),
            "calories": to_python(product.get("calories")),
            "fiber_g": to_python(product.get("fiber_g")),

            "similarity": float(round(similarity, 3)),
            "final_score": float(round(final_score, 3)),
            "match_percentage": int(match_percentage),

            "reasons": reasons,
        }

        if profile is not None:
            filtered = remove_same_product([candidate], product_id)
            if not filtered:
                continue

            filtered = remove_duplicate_names(filtered)
            filtered = filter_allergies(filtered, profile.get("allergies", []))
            filtered = filter_health(filtered, profile)
            if not filtered:
                continue

            candidate = filtered[0]

        results.append(candidate)

    results.sort(key=lambda item: item["final_score"], reverse=True)

    if profile is not None:
        results = remove_same_product(results, product_id)
        results = remove_duplicate_names(results)
        results = filter_allergies(results, profile.get("allergies", []))
        results = filter_health(results, profile)
        results = diversify_categories(results)

    # Apply category diversity
    final_results = []
    category_counts = {}

    MAX_PER_CATEGORY = min(2, max(1, top_k // 3))

    for product in results:
        category = product.get("category", "Unknown")

        if category_counts.get(category, 0) >= MAX_PER_CATEGORY:
            continue

        final_results.append(product)
        category_counts[category] = category_counts.get(category, 0) + 1

        if len(final_results) >= top_k:
            break

    seen = set()
    unique = []

    for p in final_results:
        key = p["name"].lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(p)

    return unique[:top_k]