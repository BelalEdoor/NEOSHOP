from database.product_builder import build_product
from database.generators.data import MILKS
from database import nutrition

PRODUCTS = []

barcode = 100000000001

for item in MILKS:

    PRODUCTS.append(
        build_product(
            template=getattr(nutrition, item["template"]),
            name=item["name"],
            name_ar=item["name_ar"],
            brand=item["brand"],
            category="Dairy",
            subcategory="Milk" if "Milk" in item["name"] else "Plant Milk",
            price=item["price"],
            barcode=str(barcode),
            description=item["name"],
            ingredients=item["ingredients"],
            allergens=item["allergens"],
        )
    )

    barcode += 1