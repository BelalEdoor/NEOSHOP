"""
explanation_generator.py

Generates customer-friendly explanations for AI decisions.
"""


def generate_explanation(profile, product, health_result):
    """
    Generate a natural explanation for the AI decision.

    Parameters
    ----------
    profile : dict
        User profile.

    product : dict
        Product information.

    health_result : dict
        Result returned by check_product_safety().

    Returns
    -------
    str
    """

    # Safe product
    if health_result["risk_level"] == "none":

        return (
            f'"{product["name"]}" appears suitable based on '
            "your saved allergies and health profile."
        )

    # Allergy warning
    if health_result["matched_allergies"]:

        allergies = ", ".join(
            health_result["matched_allergies"]
        )

        return (
            f'"{product["name"]}" contains {allergies}, '
            "which matches one or more allergies saved in your profile. "
            "We recommend choosing one of the safer alternatives below."
        )

    # Health condition warning
    if health_result["matched_conditions"]:

        conditions = ", ".join(
            health_result["matched_conditions"]
        )

        return (
            f'This product may not be suitable because of your '
            f'health condition ({conditions}). '
            "Please review the suggested alternatives."
        )

    # Fallback
    return "AI analysis completed."