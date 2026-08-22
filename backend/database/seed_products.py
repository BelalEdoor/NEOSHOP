import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import SessionLocal
from models.product import Product
from models.recommendation_engine import Allergen, ProductAllergen

db: Session = SessionLocal()

# Clear existing data
db.query(ProductAllergen).delete()
db.query(Product).delete()
db.commit()

df = pd.read_csv("database/products.csv")


def infer_allergens(row):
    """
    Infer allergens if the CSV allergen column is empty.
    """

    allergens = []

    # Existing CSV value
    if pd.notna(row["allergens"]) and str(row["allergens"]).strip():
        allergens.extend(
            [
                a.strip().lower()
                for a in str(row["allergens"]).split(",")
                if a.strip()
            ]
        )

    name = str(row["name"]).lower()
    category = str(row["category"]).lower()
    subcategory = str(row["subcategory"]).lower()

    # ---------- Dairy ----------
    if category == "dairy":
        allergens.append("milk")

    # ---------- Nuts ----------
    if subcategory == "nuts":
        allergens.append("nuts")

    if "almond" in name:
        allergens.append("nuts")

    if "cashew" in name:
        allergens.append("nuts")

    if "pistachio" in name:
        allergens.append("nuts")

    if "walnut" in name:
        allergens.append("nuts")

    if "hazelnut" in name:
        allergens.append("nuts")

    # ---------- Peanuts ----------
    if "peanut" in name:
        allergens.append("peanuts")

    # ---------- Soy ----------
    if "soy" in name:
        allergens.append("soy")

    # ---------- Fish ----------
    if "salmon" in name:
        allergens.append("fish")

    if "tuna" in name:
        allergens.append("fish")

    # ---------- Eggs ----------
    if "egg" in name:
        allergens.append("eggs")

    # ---------- Gluten ----------
    if subcategory in ["bread", "pastry", "pasta"]:
        allergens.append("gluten")

    if "bread" in name:
        allergens.append("gluten")

    if "croissant" in name:
        allergens.append("gluten")

    if "bagel" in name:
        allergens.append("gluten")

    if "muffin" in name:
        allergens.append("gluten")

    if "donut" in name:
        allergens.append("gluten")

    if "toast" in name:
        allergens.append("gluten")

    if "sourdough" in name:
        allergens.append("gluten")

    if "soy sauce" in name:
        allergens.append("gluten")

    # Remove duplicates
    return list(set(allergens))


for _, row in df.iterrows():

    data = row.where(pd.notnull(row), None).to_dict()

    product = Product(**data)

    db.add(product)
    db.flush()

    allergen_names = infer_allergens(row)

    for allergen_name in allergen_names:

        allergen = (
            db.query(Allergen)
            .filter(Allergen.name == allergen_name)
            .first()
        )

        if allergen:
            print(f"✓ Linking {product.name} -> {allergen.name}")

            db.add(
                ProductAllergen(
                    product_id=product.id,
                    allergen_id=allergen.id,
                )
            )

db.commit()

print(f"Inserted {len(df)} products.")