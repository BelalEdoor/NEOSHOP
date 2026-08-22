from data_loader import load_products
from embeddings import generate_embeddings
from vector_store import build_index, save_index

products = load_products()

embeddings = generate_embeddings(products)


index = build_index(
    embeddings
)


save_index(
    index,
    products
)


print(
    "Recommendation system built successfully"
)