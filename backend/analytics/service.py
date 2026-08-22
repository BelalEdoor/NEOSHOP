from analytics.sales import (
    get_sales_overview,
    get_top_products,
    get_inventory_overview,
    get_product_performance,
    get_category_performance,
    get_inventory_alerts,
    get_sales_trends,
    get_business_insights,
)

class AnalyticsService:

    @staticmethod
    def sales_overview(db):
        return get_sales_overview(db)

    @staticmethod
    def top_products(db, limit=10):
        return get_top_products(db, limit)

    @staticmethod
    def inventory_overview(db):
        return get_inventory_overview(db)

    @staticmethod
    def product_performance(db, limit=50):
        return get_product_performance(db, limit)

    @staticmethod
    def category_performance(db):
        return get_category_performance(db)

    @staticmethod
    def inventory_alerts(db):
        return get_inventory_alerts(db)

    @staticmethod
    def sales_trends(db, days=30):
        return get_sales_trends(db, days)

    @staticmethod
    def business_insights(db):
        return get_business_insights(db)