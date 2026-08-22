from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


def create_product_text(product):

    return f"""
    Product name:
    {product['name']}

    Category:
    {product['category']}

    Brand:
    {product['brand']}

    Description:
    {product['description']}

    Ingredients:
    {product['ingredients']}

    Allergens:
    {product['allergens']}
    """


def generate_embeddings(products):

    texts = []

    for _, row in products.iterrows():
        texts.append(create_product_text(row))


    embeddings = model.encode(
        texts,
        show_progress_bar=True
    )

    return embeddings