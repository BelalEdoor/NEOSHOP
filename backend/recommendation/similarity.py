def similarity_score(product, candidate):
    score = 0

    if product["subcategory"] == candidate.subcategory:
        score += 50

    if product["brand"] == candidate.brand:
        score += 20

    # Price similarity
    if (
        product.get("price")
        and candidate.price
        and abs(product["price"] - candidate.price) <= 1
    ):
        score += 10

    return score

