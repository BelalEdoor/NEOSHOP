"""Seed database with products and demo users"""
import csv
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, engine, Base
from models.user import User
from models.product import Product
from core.security import hash_password
import json

Base.metadata.create_all(bind=engine)

PRODUCTS = [
    {"name":"Whole Milk 1L","name_ar":"حليب كامل الدسم","price":1.50,"barcode":"6001001001001","quantity":200,"category":"Dairy","brand":"FreshFarm","description":"Fresh whole milk","ingredients":"whole milk","allergens":"milk","location_x":0,"location_y":0,"section":"A1"},
    {"name":"Greek Yogurt 500g","name_ar":"زبادي يوناني","price":2.20,"barcode":"6001001001002","quantity":150,"category":"Dairy","brand":"FreshFarm","description":"Creamy Greek yogurt","ingredients":"whole milk, live cultures","allergens":"milk","location_x":1,"location_y":0,"section":"A1"},
    {"name":"Cheddar Cheese 250g","name_ar":"جبن شيدر","price":3.80,"barcode":"6001001001003","quantity":100,"category":"Dairy","brand":"GoldenBlock","description":"Matured cheddar","ingredients":"milk, salt, cultures, enzymes","allergens":"milk","location_x":2,"location_y":0,"section":"A1"},
    {"name":"Butter 250g","name_ar":"زبدة","price":2.80,"barcode":"6001001002001","quantity":90,"category":"Dairy","brand":"FreshFarm","description":"Unsalted butter","ingredients":"cream, milk","allergens":"milk","location_x":0,"location_y":0,"section":"A2"},
    {"name":"Whole Wheat Bread","name_ar":"خبز القمح الكامل","price":1.20,"barcode":"6001002001001","quantity":80,"category":"Bakery","brand":"GoldenBake","description":"Whole wheat loaf","ingredients":"whole wheat flour, water, yeast, salt","allergens":"gluten, wheat","location_x":0,"location_y":1,"section":"B1"},
    {"name":"Croissant x4","name_ar":"كرواسون","price":2.50,"barcode":"6001002001002","quantity":60,"category":"Bakery","brand":"GoldenBake","description":"Buttery croissants","ingredients":"flour, butter, eggs, milk, sugar, yeast","allergens":"gluten, milk, eggs","location_x":1,"location_y":1,"section":"B1"},
    {"name":"Pita Bread x6","name_ar":"خبز عربي","price":0.90,"barcode":"6001002002001","quantity":120,"category":"Bakery","brand":"GoldenBake","description":"Soft pita bread","ingredients":"wheat flour, water, yeast, salt","allergens":"gluten, wheat","location_x":0,"location_y":1,"section":"B2"},
    {"name":"Mixed Nuts 200g","name_ar":"مكسرات مشكلة","price":4.50,"barcode":"6001003001001","quantity":120,"category":"Snacks","brand":"NutHouse","description":"Roasted mixed nuts","ingredients":"almonds, cashews, walnuts, peanuts, salt","allergens":"nuts, peanuts","location_x":0,"location_y":2,"section":"C1"},
    {"name":"Peanut Butter 340g","name_ar":"زبدة الفول السوداني","price":3.20,"barcode":"6001003001002","quantity":90,"category":"Snacks","brand":"NutHouse","description":"Creamy peanut butter","ingredients":"peanuts, salt, palm oil","allergens":"peanuts","location_x":1,"location_y":2,"section":"C1"},
    {"name":"Dark Chocolate 100g","name_ar":"شوكولاتة داكنة","price":2.00,"barcode":"6001003001004","quantity":200,"category":"Snacks","brand":"ChocoWorld","description":"70% cocoa dark chocolate","ingredients":"cocoa mass, sugar, cocoa butter","allergens":"milk","location_x":3,"location_y":2,"section":"C2"},
    {"name":"Orange Juice 1L","name_ar":"عصير برتقال","price":2.00,"barcode":"6001004001001","quantity":200,"category":"Beverages","brand":"SunFresh","description":"100% natural OJ","ingredients":"orange juice","allergens":"","location_x":0,"location_y":3,"section":"D1"},
    {"name":"Almond Milk 1L","name_ar":"حليب اللوز","price":2.80,"barcode":"6001004001002","quantity":100,"category":"Beverages","brand":"PlantMilk","description":"Unsweetened almond milk","ingredients":"water, almonds, calcium carbonate","allergens":"nuts","location_x":1,"location_y":3,"section":"D1"},
    {"name":"Oat Milk 1L","name_ar":"حليب الشوفان","price":2.60,"barcode":"6001004001003","quantity":110,"category":"Beverages","brand":"PlantMilk","description":"Creamy oat milk","ingredients":"water, oats, rapeseed oil, salt","allergens":"gluten","location_x":2,"location_y":3,"section":"D2"},
    {"name":"Coconut Water 330ml","name_ar":"ماء جوز الهند","price":1.60,"barcode":"6001004001004","quantity":300,"category":"Beverages","brand":"TropicFresh","description":"Natural coconut water","ingredients":"coconut water","allergens":"","location_x":3,"location_y":3,"section":"D2"},
    {"name":"Organic Eggs x12","name_ar":"بيض عضوي","price":3.50,"barcode":"6001005001001","quantity":150,"category":"Produce","brand":"GreenFarm","description":"Free-range organic eggs","ingredients":"eggs","allergens":"eggs","location_x":0,"location_y":4,"section":"E1"},
    {"name":"Baby Spinach 150g","name_ar":"سبانخ طازجة","price":1.90,"barcode":"6001005001002","quantity":80,"category":"Produce","brand":"GreenFarm","description":"Tender baby spinach","ingredients":"spinach","allergens":"","location_x":1,"location_y":4,"section":"E1"},
    {"name":"Chicken Breast 500g","name_ar":"صدر دجاج","price":5.50,"barcode":"6001006001001","quantity":70,"category":"Meat","brand":"FarmFresh","description":"Boneless chicken breast","ingredients":"chicken breast","allergens":"","location_x":0,"location_y":5,"section":"F1"},
    {"name":"Salmon Fillet 300g","name_ar":"فيليه سلمون","price":7.80,"barcode":"6001006001002","quantity":50,"category":"Meat","brand":"OceanFresh","description":"Atlantic salmon fillet","ingredients":"salmon","allergens":"fish","location_x":1,"location_y":5,"section":"F1"},
    {"name":"Basmati Rice 1kg","name_ar":"أرز بسمتي","price":2.90,"barcode":"6001007001001","quantity":200,"category":"Pantry","brand":"RiceKing","description":"Premium basmati rice","ingredients":"basmati rice","allergens":"","location_x":0,"location_y":6,"section":"A2"},
    {"name":"Extra Virgin Olive Oil 500ml","name_ar":"زيت زيتون بكر ممتاز","price":6.50,"barcode":"6001007001002","quantity":120,"category":"Pantry","brand":"MedOlive","description":"Cold-pressed olive oil","ingredients":"olive oil","allergens":"","location_x":1,"location_y":6,"section":"A2"},
    {"name":"Soy Sauce 150ml","name_ar":"صلصة الصويا","price":1.40,"barcode":"6001007001003","quantity":180,"category":"Pantry","brand":"AsiaKitchen","description":"Traditional soy sauce","ingredients":"water, soybeans, wheat, salt","allergens":"soy, gluten","location_x":2,"location_y":6,"section":"B2"},
]


def seed_products_only(db):
    """Seed the complete catalog for main.py auto-seed."""
    catalog_path = Path(__file__).parent / "database" / "products.csv"
    if catalog_path.exists():
        numeric_fields = {
            "price", "quantity", "location_x", "location_y", "calories",
            "sugar_g", "sodium_mg", "protein_g", "fat_g", "saturated_fat_g",
            "carbohydrates_g", "fiber_g", "cholesterol_mg", "old_price",
        }
        boolean_fields = {
            "is_vegan", "is_vegetarian", "is_gluten_free", "is_lactose_free", "is_on_offer",
        }
        products = []
        with catalog_path.open(newline="", encoding="utf-8-sig") as catalog_file:
            for row in csv.DictReader(catalog_file):
                product = {key: (value.strip() or None) for key, value in row.items()}
                for key in numeric_fields:
                    if product.get(key) is not None:
                        product[key] = float(product[key])
                        if key in {"quantity", "location_x", "location_y"}:
                            product[key] = int(product[key])
                for key in boolean_fields:
                    product[key] = str(product.get(key)).lower() == "true"
                products.append(product)
    else:
        products = PRODUCTS

    for p in products:
        db.add(Product(**p))
    db.commit()


def seed():
    """Full seed — run manually: python seed.py"""
    db = SessionLocal()
    try:
        # Users
        if db.query(User).count() == 0:
            db.add(User(name="Demo Cashier", email="demo@neoshop.com",  password_hash=hash_password("demo1234"),  allergies=json.dumps([])))
            db.add(User(name="Admin Owner",  email="admin@neoshop.com", password_hash=hash_password("admin1234"), allergies=json.dumps([])))
            db.commit()
            print("✅ Users: demo@neoshop.com/demo1234 | admin@neoshop.com/admin1234")
        else:
            print("⚠️  Users already exist")

        # Products
        existing = db.query(Product).count()
        if existing == 0:
            seed_products_only(db)
            print(f"✅ Seeded {len(PRODUCTS)} products")
        else:
            print(f"⚠️  {existing} products already exist — skipping")

        print("\n🚀 Ready!")
        print("   Backend:  uvicorn main:app --reload")
        print("   Frontend: cd frontend && npm run dev")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
