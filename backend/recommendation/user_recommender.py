from recommendation.recommender import recommend
from recommendation.user_profile import get_user_profile
from recommendation.preference_builder import build_preference_text
from recommendation.health_checker import check_product_health
from recommendation.filters import *


def recommend_for_user(user_id, profile=None, product=None, product_health=None):
    """
    Generate personalized product recommendations for a user.
    """

    if profile is None:
        profile = get_user_profile(user_id)

    if profile is None:
        return []

    user_conditions = profile["health_conditions"]

    # Build preference text from purchase history
    preference_text = build_preference_text(profile)

    # If the user has no purchase history, use a generic query
    if not preference_text:
        preference_text = "popular grocery products"

    # Retrieve similar products
    results = recommend(
        None,
        preference_text,
        top_k=40
    )

    if product is not None:
        results = remove_same_product(results, product["id"])

    results = remove_duplicate_names(results)
    results = filter_allergies(results, profile.get("allergies", []))
    results = filter_health(results, profile)

    if product_health is not None:
        results = filter_healthier_than_scanned(results, product_health)

    results = diversify_categories(results)
    results = results[:5]

    # Filter products using the health checker
    filtered = []
    seen = set()

    for product in results:
        health = check_product_health(profile, product)

        if health["risk_level"] in ["Low", "Medium"] and product["id"] not in seen:
            reasons = list(product.get("reasons", []))

            reasons.append("Safe for your current allergy profile")

            if health["risk_level"] == "Medium":
                reasons.append("Consume in moderation")

            if health["matched_conditions"]:
                for condition in health["matched_conditions"]:
                    reasons.append(f"Suitable for {condition}")
            elif user_conditions:
                reasons.append("Suitable for your health conditions")
            else:
                reasons.append("No health restrictions found")

            product["reasons"] = reasons
            product["health"] = health

            filtered.append(product)
            seen.add(product["id"])

    filtered.sort(
        key=lambda p: p.get("final_score", 0),
        reverse=True
    )

    recommendations = []

    for product in filtered[:5]:
        recommendations.append({
            "id": product["id"],
            "name": product["name"],
            "category": product["category"],
            "match_percentage": product.get("match_percentage", 0),
            "final_score": product.get("final_score", 0),
            "reasons": product.get("reasons", []),
            "health_score": product.get("health", {}).get("health_score"),
            "risk_level": product.get("health", {}).get("risk_level"),
            "warnings": product.get("health", {}).get("warnings"),
        })

    return recommendations