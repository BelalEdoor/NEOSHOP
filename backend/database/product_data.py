from database.nutrition import *

PRODUCTS = [

    {
        **MILK,
        "name": "Whole Milk 1L",
        "name_ar": "حليب كامل الدسم",
        "brand": "FreshFarm",
        "category": "Dairy",
        "subcategory": "Milk",
        "price": 4.99,
        "barcode": "100000000001",
        "description": "Pasteurized whole milk.",
        "ingredients": "Pasteurized whole milk",
        "allergens": "Milk",
    },

    {
        **LOW_FAT_MILK,
        "name": "Low Fat Milk 1L",
        "name_ar": "حليب قليل الدسم",
        "brand": "FreshFarm",
        "category": "Dairy",
        "subcategory": "Milk",
        "price": 5.49,
        "barcode": "100000000002",
        "description": "Pasteurized low-fat milk.",
        "ingredients": "Low-fat milk",
        "allergens": "Milk",
    },

    {
        **SKIM_MILK,
        "name": "Skim Milk 1L",
        "name_ar": "حليب خالي الدسم",
        "brand": "FreshFarm",
        "category": "Dairy",
        "subcategory": "Milk",
        "price": 5.79,
        "barcode": "100000000003",
        "description": "Fat-free milk.",
        "ingredients": "Skim milk",
        "allergens": "Milk",
    },

    {
        **LACTOSE_FREE_MILK,
        "name": "Lactose-Free Milk 1L",
        "name_ar": "حليب خالي من اللاكتوز",
        "brand": "FreshFarm",
        "category": "Dairy",
        "subcategory": "Milk",
        "price": 6.99,
        "barcode": "100000000004",
        "description": "Milk suitable for lactose intolerance.",
        "ingredients": "Lactose-free milk",
        "allergens": "Milk",
    },

    {
        **PLANT_MILK,
        "name": "Almond Milk 1L",
        "name_ar": "حليب اللوز",
        "brand": "Alpro",
        "category": "Dairy",
        "subcategory": "Plant Milk",
        "price": 8.99,
        "barcode": "100000000005",
        "description": "Unsweetened almond drink.",
        "ingredients": "Water, Almonds",
        "allergens": "Tree Nuts",
    },

]