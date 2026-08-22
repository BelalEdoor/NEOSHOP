from recommendation.user_profile import get_user_profile
from recommendation.user_recommender import recommend_for_user
from recommendation.health_checker import check_product_health
from recommendation.alternative_generator import generate_safe_alternatives
from recommendation.explanation_generator import generate_explanation


def analyze_product(db, user_id: int, product: dict):
    """
    Central AI pipeline for analyzing a scanned product.

    Parameters
    ----------
    db : Session
        SQLAlchemy DB session — needed by generate_safe_alternatives()
        which queries the Product table for candidate alternatives.

    user_id : int
        Customer ID.

    product : dict
        Product information returned from the database.

    Returns
    -------
    dict
        Unified AI response.
    """

    # -------------------------------------------------
    # 1. Load User Profile
    # -------------------------------------------------
    profile = get_user_profile(user_id)

    if profile is None:
        return {
            "success": False,
            "message": "User not found."
        }

    # -------------------------------------------------
    # 2. Health Analysis
    # -------------------------------------------------
    health_result = check_product_health(
        profile,
        product
    )

    # -------------------------------------------------
    # 3. Personalized Recommendations
    # -------------------------------------------------
    recommendations = recommend_for_user(user_id)

    # -------------------------------------------------
    # 4. Safe Alternatives
    # -------------------------------------------------
    safe_alternatives = []

    if not health_result["safe"]:

        safe_alternatives = generate_safe_alternatives(
            db,
            profile,
            product
        )

    # -------------------------------------------------
    # 5. AI Explanation
    # -------------------------------------------------
    reason = generate_explanation(
        profile,
        product,
        health_result
    )

    # -------------------------------------------------
    # 6. Frontend Actions
    # -------------------------------------------------
    action = {

        "allow_add": health_result["safe"],

        "show_warning": not health_result["safe"],

        "show_alternatives": not health_result["safe"],

        "allow_buy_for_family": True

    }

    # -------------------------------------------------
    # 7. Unified AI Response
    # -------------------------------------------------
    return {

        "success": True,

        "product": product,

        "health": health_result,

        "recommendations": recommendations,

        "safe_alternatives": safe_alternatives,

        "reason": reason,

        "action": action

    }