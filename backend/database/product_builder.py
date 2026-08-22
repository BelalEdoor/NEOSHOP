"""
Helper functions for building NeoShop products.
"""

from copy import deepcopy


def build_product(
    *,
    template,
    name,
    name_ar,
    brand,
    category,
    subcategory,
    price,
    barcode,
    description="",
    ingredients="",
    allergens="",
    image_url="",
):
    """
    Build a product dictionary using a nutrition template.

    Example:
        build_product(
            template=MILK,
            name="Whole Milk 1L",
            ...
        )
    """

    product = deepcopy(template)

    product.update(
        {
            "name": name,
            "name_ar": name_ar,
            "brand": brand,
            "category": category,
            "subcategory": subcategory,
            "price": price,
            "barcode": barcode,
            "description": description,
            "ingredients": ingredients,
            "allergens": allergens,
            "image_url": image_url,
        }
    )

    return product


def build_products(products):
    """
    Simply returns the list.

    Makes every generator file look cleaner.
    """
    return products