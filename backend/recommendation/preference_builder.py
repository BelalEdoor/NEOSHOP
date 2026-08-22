"""
recommendation/preference_builder.py
===================================

Builds a preference text from the user's purchase history.

This text is later embedded and used to retrieve similar products.
"""

from typing import Dict


def build_preference_text(profile: Dict) -> str:
    """
    Build a preference sentence from the user's purchase history.

    Parameters
    ----------
    profile : dict
        Output of get_user_profile()

    Returns
    -------
    str
        Preference text used by the recommender.
    """

    purchases = profile.get("purchases", [])

    if not purchases:
        return ""

    parts = []

    for item in purchases:
        if not isinstance(item, dict):
            continue

        for field in ("name", "category", "brand"):
            value = item.get(field)
            if value:
                parts.append(str(value))

    return " ".join(parts)