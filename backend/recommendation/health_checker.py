"""
recommendation/health_checker.py
================================

AI Health Checker for NeoShop.

Analyzes whether a product is suitable for a customer based on:

- Allergies
- Health conditions
- Nutrition information

Returns a unified health report for the AI pipeline.
"""

from typing import Dict, List


# ---------------------------------------------------------
# Health Score Penalties
# ---------------------------------------------------------

MAX_SCORE = 100

ALLERGY_PENALTY = 50

HIGH_SUGAR_PENALTY = 20
MEDIUM_SUGAR_PENALTY = 10

HIGH_SODIUM_PENALTY = 20
MEDIUM_SODIUM_PENALTY = 10

HIGH_CHOLESTEROL_PENALTY = 20
MEDIUM_CHOLESTEROL_PENALTY = 10

GENERAL_WARNING_PENALTY = 5

ALLERGY_GROUPS = {

    "milk": [
        "milk",
        "cheese",
        "butter",
        "cream",
        "yogurt",
        "lactose",
    ],

    "nuts": [
        "nut",
        "nuts",
        "almond",
        "almonds",
        "pistachio",
        "pistachios",
        "cashew",
        "cashews",
        "walnut",
        "walnuts",
        "hazelnut",
        "hazelnuts",
        "peanut",
        "peanuts",
    ],

    "fish": [
        "fish",
        "salmon",
        "tuna",
        "sardine",
        "cod",
        "anchovy",
    ],

    "eggs": [
        "egg",
        "eggs",
    ],

    "soy": [
        "soy",
        "soybean",
        "soybeans",
    ],

    "gluten": [
        "gluten",
        "wheat",
        "barley",
        "rye",
    ],
}


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def _safe_float(value, default=0.0):
    """
    Convert value to float safely.
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value):
    """
    Convert text to lowercase.

    Handles None safely.
    """

    if value is None:
        return ""

    return str(value).lower()


def _get_conditions(profile):
    """
    Return a normalized set of health conditions for the user.
    """

    return {
        condition.lower()
        for condition in profile.get("health_conditions", [])
    }


# ---------------------------------------------------------
# Allergy Checker
# ---------------------------------------------------------

def _check_allergies(
    profile: Dict,
    product: Dict,
    warnings: List[str],
    matched_allergies: List[str]
):
    """
    Check whether the product contains any user allergens.

    Returns
    -------
    int
        Penalty points.
    """

    penalty = 0

    user_allergies = [
        allergy.lower()
        for allergy in profile.get("allergies", [])
    ]

    search_text = " ".join([
        _normalize_text(product.get("ingredients")),
        _normalize_text(product.get("allergens")),
        _normalize_text(product.get("category")),
        _normalize_text(product.get("subcategory")),
        _normalize_text(product.get("description")),
    ])

    for allergy in user_allergies:

        allergy = allergy.lower()

        keywords = ALLERGY_GROUPS.get(allergy, [allergy])

        if any(keyword in search_text for keyword in keywords):

            matched_allergies.append(allergy.title())

            warnings.append(
                f"Contains allergen: {allergy.title()}."
            )

            penalty += ALLERGY_PENALTY

    return penalty


# ---------------------------------------------------------
# Diabetes Checker
# ---------------------------------------------------------

def _check_diabetes(
    profile: Dict,
    product: Dict,
    warnings: List[str],
    matched_conditions: List[str]
):
    """
    Check sugar content for diabetic users.

    Sugar thresholds (grams):

        <=5      Excellent
        5-10     Moderate
        10-15    High
        >15      Very High
    """

    conditions = _get_conditions(profile)

    if "diabetes" not in conditions:
        return 0

    matched_conditions.append("Diabetes")

    sugar = _safe_float(
        product.get("sugar_g")
    )

    penalty = 0

    if sugar > 15:

        warnings.append(
            "Very high sugar content."
        )

        penalty += HIGH_SUGAR_PENALTY

    elif sugar > 10:

        warnings.append(
            "High sugar content."
        )

        penalty += HIGH_SUGAR_PENALTY

    elif sugar > 5:

        warnings.append(
            "Moderate sugar content."
        )

        penalty += MEDIUM_SUGAR_PENALTY

    return penalty


# ---------------------------------------------------------
# Hypertension Checker
# ---------------------------------------------------------

def _check_hypertension(
    profile: Dict,
    product: Dict,
    warnings: List[str],
    matched_conditions: List[str]
):
    """
    Check sodium level for users with hypertension.
    """

    conditions = _get_conditions(profile)

    if "hypertension" not in conditions:
        return 0

    matched_conditions.append("Hypertension")

    sodium = _safe_float(product.get("sodium_mg"))

    penalty = 0

    if sodium > 400:

        warnings.append("Very high sodium content.")

        penalty += HIGH_SODIUM_PENALTY

    elif sodium > 140:

        warnings.append("High sodium content.")

        penalty += MEDIUM_SODIUM_PENALTY

    return penalty


# ---------------------------------------------------------
# Cholesterol Checker
# ---------------------------------------------------------

def _check_cholesterol(
    profile: Dict,
    product: Dict,
    warnings: List[str],
    matched_conditions: List[str]
):
    """
    Check cholesterol and saturated fat.
    """

    conditions = _get_conditions(profile)

    if "high cholesterol" not in conditions:
        return 0

    matched_conditions.append("High Cholesterol")

    cholesterol = _safe_float(
        product.get("cholesterol_mg")
    )

    saturated_fat = _safe_float(
        product.get("saturated_fat_g")
    )

    penalty = 0

    if cholesterol > 20:

        warnings.append("High cholesterol level.")

        penalty += MEDIUM_CHOLESTEROL_PENALTY

    if saturated_fat > 5:

        warnings.append("High saturated fat.")

        penalty += HIGH_CHOLESTEROL_PENALTY

    return penalty


# ---------------------------------------------------------
# General Nutrition Checker
# ---------------------------------------------------------

def _check_general_nutrition(
    product: Dict,
    warnings: List[str]
):
    """
    Nutrition checks for every user.
    """

    penalty = 0

    calories = _safe_float(product.get("calories"))
    fiber = _safe_float(product.get("fiber_g"))

    if calories > 400:

        warnings.append("High calorie product.")

        penalty += GENERAL_WARNING_PENALTY

    if fiber < 2:

        warnings.append("Low dietary fiber.")

        penalty += GENERAL_WARNING_PENALTY

    return penalty


# ---------------------------------------------------------
# Risk Calculation
# ---------------------------------------------------------

def _calculate_risk(score: int):

    if score >= 80:
        return True, "Low"

    if score >= 60:
        return False, "Medium"

    if score >= 40:
        return False, "High"

    return False, "Critical"


# ---------------------------------------------------------
# Main Function
# ---------------------------------------------------------

def check_product_health(
    profile: Dict,
    product: Dict
):
    """
    Main Health Checker.

    Returns
    -------
    dict
    """

    warnings = []

    matched_allergies = []

    matched_conditions = []

    score = MAX_SCORE

    score -= _check_allergies(
        profile,
        product,
        warnings,
        matched_allergies
    )

    score -= _check_diabetes(
        profile,
        product,
        warnings,
        matched_conditions
    )

    score -= _check_hypertension(
        profile,
        product,
        warnings,
        matched_conditions
    )

    score -= _check_cholesterol(
        profile,
        product,
        warnings,
        matched_conditions
    )

    score -= _check_general_nutrition(
        product,
        warnings
    )

    score = max(0, min(MAX_SCORE, score))

    safe, risk = _calculate_risk(score)

    return {

        "safe": safe,

        "health_score": score,

        "risk_level": risk,

        "warnings": warnings,

        "matched_allergies": list(
            dict.fromkeys(matched_allergies)
        ),

        "matched_conditions": list(
            dict.fromkeys(matched_conditions)
        )
    }