from collections import defaultdict


def remove_same_product(results, scanned_product_id):
    return [
        p for p in results
        if p["id"] != scanned_product_id
    ]


def remove_duplicate_names(results):
    seen = set()
    filtered = []

    for product in results:
        key = product["name"].strip().lower()

        if key in seen:
            continue

        seen.add(key)
        filtered.append(product)

    return filtered


def filter_allergies(results, user_allergies):
    if not user_allergies:
        return results

    allergies = {
        a.lower().strip()
        for a in user_allergies
    }

    filtered = []

    for product in results:

        text = (
            str(product.get("allergens", "")) +
            " " +
            str(product.get("ingredients", ""))
        ).lower()

        if any(a in text for a in allergies):
            continue

        filtered.append(product)

    return filtered


def filter_health(results, profile):

    conditions = {
        c.lower()
        for c in profile.get("health_conditions", [])
    }

    filtered = []

    for p in results:

        sugar = float(p.get("sugar_g") or 0)
        sodium = float(p.get("sodium_mg") or 0)
        calories = float(p.get("calories") or 0)

        unsafe = False

        if "diabetes" in conditions and sugar > 15:
            unsafe = True

        if "hypertension" in conditions and sodium > 400:
            unsafe = True

        if "obesity" in conditions and calories > 300:
            unsafe = True

        if unsafe:
            continue

        filtered.append(p)

    return filtered


def filter_healthier_than_scanned(results, scanned_product):

    scanned_score = scanned_product.get(
        "health_score",
        0
    )

    filtered = []

    for product in results:

        score = 100

        if product.get("calories"):
            score -= product["calories"] / 10

        if product.get("sodium_mg"):
            score -= product["sodium_mg"] / 100

        if product.get("sugar_g"):
            score -= product["sugar_g"]

        if score >= scanned_score:
            filtered.append(product)

    return filtered


def diversify_categories(results, max_per_category=2):

    final = []
    counter = defaultdict(int)

    for product in results:

        cat = product.get("category", "Unknown")

        if counter[cat] >= max_per_category:
            continue

        counter[cat] += 1

        final.append(product)

    return final