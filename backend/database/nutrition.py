"""
Reusable nutrition templates for NeoShop products.

Values are approximate per 100g (or 100ml for beverages).
"""

# ==========================================================
# DAIRY
# ==========================================================

MILK = {
    "calories": 64,
    "protein_g": 3.3,
    "fat_g": 3.6,
    "saturated_fat_g": 2.2,
    "carbohydrates_g": 4.8,
    "sugar_g": 4.8,
    "fiber_g": 0.0,
    "sodium_mg": 44,
    "cholesterol_mg": 14,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": False,
}

LOW_FAT_MILK = {
    **MILK,
    "calories": 46,
    "fat_g": 1.5,
    "saturated_fat_g": 1.0,
    "cholesterol_mg": 7,
}

SKIM_MILK = {
    **MILK,
    "calories": 34,
    "fat_g": 0.1,
    "saturated_fat_g": 0.1,
    "cholesterol_mg": 2,
}

LACTOSE_FREE_MILK = {
    **MILK,
    "is_lactose_free": True,
}

PLANT_MILK = {
    "calories": 20,
    "protein_g": 1.0,
    "fat_g": 1.4,
    "saturated_fat_g": 0.2,
    "carbohydrates_g": 1.0,
    "sugar_g": 0.2,
    "fiber_g": 0.5,
    "sodium_mg": 100,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

YOGURT = {
    "calories": 61,
    "protein_g": 3.5,
    "fat_g": 3.3,
    "saturated_fat_g": 2.1,
    "carbohydrates_g": 4.7,
    "sugar_g": 4.7,
    "fiber_g": 0,
    "sodium_mg": 46,
    "cholesterol_mg": 13,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": False,
}

CHEESE = {
    "calories": 402,
    "protein_g": 25,
    "fat_g": 33,
    "saturated_fat_g": 19,
    "carbohydrates_g": 1.3,
    "sugar_g": 0.5,
    "fiber_g": 0,
    "sodium_mg": 620,
    "cholesterol_mg": 105,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": False,
}

BUTTER = {
    "calories": 717,
    "protein_g": 1,
    "fat_g": 81,
    "saturated_fat_g": 51,
    "carbohydrates_g": 0.1,
    "sugar_g": 0.1,
    "fiber_g": 0,
    "sodium_mg": 11,
    "cholesterol_mg": 215,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": False,
}

# ==========================================================
# BAKERY
# ==========================================================

BREAD = {
    "calories": 250,
    "protein_g": 9,
    "fat_g": 3,
    "saturated_fat_g": 0.7,
    "carbohydrates_g": 49,
    "sugar_g": 5,
    "fiber_g": 7,
    "sodium_mg": 490,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": False,
    "is_lactose_free": True,
}

PASTRY = {
    "calories": 406,
    "protein_g": 8,
    "fat_g": 21,
    "saturated_fat_g": 11,
    "carbohydrates_g": 46,
    "sugar_g": 11,
    "fiber_g": 2,
    "sodium_mg": 380,
    "cholesterol_mg": 48,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": False,
    "is_lactose_free": False,
}

# ==========================================================
# BEVERAGES
# ==========================================================

JUICE = {
    "calories": 45,
    "protein_g": 0.5,
    "fat_g": 0,
    "saturated_fat_g": 0,
    "carbohydrates_g": 10.5,
    "sugar_g": 9,
    "fiber_g": 0.2,
    "sodium_mg": 2,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

WATER = {
    "calories": 0,
    "protein_g": 0,
    "fat_g": 0,
    "saturated_fat_g": 0,
    "carbohydrates_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "sodium_mg": 0,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

SOFT_DRINK = {
    "calories": 42,
    "protein_g": 0,
    "fat_g": 0,
    "saturated_fat_g": 0,
    "carbohydrates_g": 10.6,
    "sugar_g": 10.6,
    "fiber_g": 0,
    "sodium_mg": 11,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

# ==========================================================
# PRODUCE
# ==========================================================

FRUIT = {
    "calories": 52,
    "protein_g": 0.6,
    "fat_g": 0.2,
    "saturated_fat_g": 0,
    "carbohydrates_g": 14,
    "sugar_g": 10,
    "fiber_g": 2.4,
    "sodium_mg": 1,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

VEGETABLE = {
    "calories": 25,
    "protein_g": 2,
    "fat_g": 0.2,
    "saturated_fat_g": 0,
    "carbohydrates_g": 5,
    "sugar_g": 2.5,
    "fiber_g": 2.5,
    "sodium_mg": 40,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

EGGS = {
    "calories": 155,
    "protein_g": 13,
    "fat_g": 11,
    "saturated_fat_g": 3.3,
    "carbohydrates_g": 1.1,
    "sugar_g": 1.1,
    "fiber_g": 0,
    "sodium_mg": 124,
    "cholesterol_mg": 373,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

# ==========================================================
# MEAT
# ==========================================================

CHICKEN = {
    "calories": 165,
    "protein_g": 31,
    "fat_g": 3.6,
    "saturated_fat_g": 1,
    "carbohydrates_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "sodium_mg": 74,
    "cholesterol_mg": 85,
    "is_vegan": False,
    "is_vegetarian": False,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

BEEF = {
    "calories": 250,
    "protein_g": 26,
    "fat_g": 15,
    "saturated_fat_g": 6,
    "carbohydrates_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "sodium_mg": 72,
    "cholesterol_mg": 90,
    "is_vegan": False,
    "is_vegetarian": False,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

SEAFOOD = {
    "calories": 208,
    "protein_g": 20,
    "fat_g": 13,
    "saturated_fat_g": 3,
    "carbohydrates_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "sodium_mg": 59,
    "cholesterol_mg": 55,
    "is_vegan": False,
    "is_vegetarian": False,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

# ==========================================================
# PANTRY
# ==========================================================

RICE = {
    "calories": 365,
    "protein_g": 7,
    "fat_g": 0.7,
    "saturated_fat_g": 0.2,
    "carbohydrates_g": 80,
    "sugar_g": 0.1,
    "fiber_g": 1.3,
    "sodium_mg": 1,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

PASTA = {
    **RICE,
    "protein_g": 13,
    "carbohydrates_g": 75,
    "is_gluten_free": False,
}

OIL = {
    "calories": 884,
    "protein_g": 0,
    "fat_g": 100,
    "saturated_fat_g": 14,
    "carbohydrates_g": 0,
    "sugar_g": 0,
    "fiber_g": 0,
    "sodium_mg": 2,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

SAUCE = {
    "calories": 53,
    "protein_g": 5,
    "fat_g": 0.6,
    "saturated_fat_g": 0.1,
    "carbohydrates_g": 7,
    "sugar_g": 1,
    "fiber_g": 0.8,
    "sodium_mg": 900,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": False,
    "is_lactose_free": True,
}

# ==========================================================
# SNACKS
# ==========================================================

CHOCOLATE = {
    "calories": 546,
    "protein_g": 4.9,
    "fat_g": 31,
    "saturated_fat_g": 19,
    "carbohydrates_g": 61,
    "sugar_g": 48,
    "fiber_g": 7,
    "sodium_mg": 24,
    "cholesterol_mg": 8,
    "is_vegan": False,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": False,
}

NUTS = {
    "calories": 607,
    "protein_g": 20,
    "fat_g": 54,
    "saturated_fat_g": 7,
    "carbohydrates_g": 21,
    "sugar_g": 4,
    "fiber_g": 8,
    "sodium_mg": 6,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": True,
    "is_lactose_free": True,
}

CHIPS = {
    "calories": 536,
    "protein_g": 7,
    "fat_g": 34,
    "saturated_fat_g": 10,
    "carbohydrates_g": 53,
    "sugar_g": 1,
    "fiber_g": 4,
    "sodium_mg": 525,
    "cholesterol_mg": 0,
    "is_vegan": True,
    "is_vegetarian": True,
    "is_gluten_free": False,
    "is_lactose_free": True,
}