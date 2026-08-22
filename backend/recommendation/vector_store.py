import faiss
import pickle


def build_index(embeddings):

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(
        dimension
    )

    index.add(embeddings)

    return index



def save_index(index, products):

    faiss.write_index(
        index,
        "products.index"
    )


    with open(
        "products.pkl",
        "wb"
    ) as f:
        pickle.dump(
            products,
            f
        )