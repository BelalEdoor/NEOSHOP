import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_user_profile(user_id: int):
    """
    Load a user's profile, allergies, health conditions,
    and purchase history from the database.
    """

    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:

        # -----------------------------
        # Basic user information
        # -----------------------------
        user = conn.execute(
            text("""
                SELECT
                    id,
                    name,
                    age,
                    gender
                FROM users
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        ).mappings().first()

        if not user:
            return None

        # -----------------------------
        # Allergies
        # -----------------------------
        allergies = conn.execute(
            text("""
                SELECT a.name
                FROM customer_allergies ca
                JOIN allergens a
                    ON ca.allergen_id = a.id
                WHERE ca.user_id = :user_id
            """),
            {"user_id": user_id}
        ).scalars().all()

        # -----------------------------
        # Health conditions
        # -----------------------------
        conditions = conn.execute(
            text("""
                SELECT h.name
                FROM customer_health_conditions ch
                JOIN health_conditions h
                    ON ch.condition_id = h.id
                WHERE ch.user_id = :user_id
            """),
            {"user_id": user_id}
        ).scalars().all()

        # -----------------------------
        # Purchase history
        # -----------------------------
        purchases = conn.execute(
            text("""
                SELECT
                    p.id,
                    p.name,
                    p.category,
                    p.brand
                FROM shopping_sessions s
                JOIN cart_items c
                    ON s.id = c.session_id
                JOIN products p
                    ON c.product_id = p.id
                WHERE s.user_id = :user_id
            """),
            {"user_id": user_id}
        ).mappings().all()

    engine.dispose()

    return {
        "user": dict(user),
        "allergies": allergies,
        "health_conditions": conditions,
        "purchases": [dict(p) for p in purchases]
    }