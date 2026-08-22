import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def load_products():
    """
    Load all products along with their allergens from the database.
    """

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL not found in .env")

    engine = create_engine(database_url)

    query = """
SELECT
    p.id,
    p.barcode,
    p.name,
    p.name_ar,
    p.price,
    p.quantity,
    p.category,
    p.subcategory,
    p.brand,
    p.description,
    p.ingredients,
    p.image_url,
    p.location_x,
    p.location_y,
    p.section,

    p.sugar_g,
    p.sodium_mg,
    p.cholesterol_mg,
    p.saturated_fat_g,
    p.calories,
    p.fiber_g,

    COALESCE(GROUP_CONCAT(a.name SEPARATOR ','), '') AS allergens

FROM products p

LEFT JOIN product_allergens pa
    ON p.id = pa.product_id

LEFT JOIN allergens a
    ON pa.allergen_id = a.id

GROUP BY
    p.id,
    p.barcode,
    p.name,
    p.name_ar,
    p.price,
    p.quantity,
    p.category,
    p.subcategory,
    p.brand,
    p.description,
    p.ingredients,
    p.image_url,
    p.location_x,
    p.location_y,
    p.section,
    p.sugar_g,
    p.sodium_mg,
    p.cholesterol_mg,
    p.saturated_fat_g,
    p.calories,
    p.fiber_g;
"""

    try:
        with engine.connect() as connection:
            print("DATABASE_URL:", database_url)
            print("Engine type:", type(engine))
            print("Connection type:", type(connection))
            products = pd.read_sql(
                text(query),
                connection
            )

        return products

    finally:
        engine.dispose()