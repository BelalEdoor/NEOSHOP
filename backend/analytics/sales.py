from sqlalchemy import func

from models.invoice import Invoice, InvoiceStatus
from models.cart import CartItem
from models.product import Product


def get_sales_trends(db, days=30):

    rows = (
        db.query(
            func.date(Invoice.created_at).label("date"),
            func.count(Invoice.id).label("orders"),
            func.coalesce(
                func.sum(CartItem.quantity),
                0
            ).label("quantity_sold"),
            func.coalesce(
                func.sum(
                    CartItem.quantity * CartItem.unit_price
                ),
                0
            ).label("revenue"),
        )
        .join(
            CartItem,
            CartItem.session_id == Invoice.session_id
        )
        .group_by(
            func.date(Invoice.created_at)
        )
        .order_by(
            func.date(Invoice.created_at).desc()
        )
        .limit(days)
        .all()
    )

    return [
        {
            "date": str(row.date),
            "orders": int(row.orders or 0),
            "quantity_sold": int(row.quantity_sold or 0),
            "revenue": round(float(row.revenue or 0), 2),
        }
        for row in rows
    ]


def get_business_insights(db):

    alerts = get_inventory_alerts(db)
    low_stock = [
        item
        for item in alerts
        if item["alert_type"] in ("CRITICAL_STOCK", "LOW_STOCK")
    ]
    slow_sellers = [
        item
        for item in alerts
        if item["alert_type"] == "SLOW_SELLER"
    ]
    no_sales = [
        item
        for item in alerts
        if item["alert_type"] == "NO_SALES"
    ]

    insights = []

    # Low stock
    if low_stock:
        insights.append({
            "type": "LOW_STOCK",
            "severity": "WARNING",
            "title": "Low stock detected",
            "message": (
                f"{len(low_stock)} product(s) "
                "have low inventory levels."
            ),
        })

    # Slow sellers
    if slow_sellers:
        names = [
            item["product"]
            for item in slow_sellers[:5]
        ]
        insights.append({
            "type": "SLOW_SELLERS",
            "severity": "WARNING",
            "title": "Some products are selling slowly",
            "message": (
                f"{', '.join(names)} "
                "have very low recorded sales."
            ),
        })

    # Products with no sales
    if no_sales:
        insights.append({
            "type": "NO_SALES_PRODUCTS",
            "severity": "WARNING",
            "title": "Products have no recorded sales",
            "message": (
                f"{len(no_sales)} product(s) "
                "currently have no recorded sales."
            ),
        })

    # Overall inventory health
    inventory = get_inventory_overview(db)
    if (
        inventory["out_of_stock"] == 0
        and inventory["low_stock"] == 0
    ):
        insights.append({
            "type": "HEALTHY_INVENTORY",
            "severity": "INFO",
            "title": "Inventory is currently healthy",
            "message": (
                "No products are currently reported "
                "as low stock or out of stock."
            ),
        })

    return insights



def get_sales_overview(db):
    # Recorded sales = invoices that were created/sent
    # or successfully paid.
    sales_statuses = [
        InvoiceStatus.SENT,
        InvoiceStatus.PAID,
    ]
    total_revenue = (
        db.query(
            func.coalesce(
                func.sum(Invoice.total_amount),
                0
            )
        )
        .filter(
            Invoice.status.in_(sales_statuses)
        )
        .scalar()
    ) or 0
    total_orders = (
        db.query(Invoice)
        .filter(
            Invoice.status.in_(sales_statuses)
        )
        .count()
    )
    successful_orders = (
        db.query(Invoice)
        .filter(
            Invoice.status == InvoiceStatus.PAID
        )
        .count()
    )
    cancelled_orders = (
        db.query(Invoice)
        .filter(
            Invoice.status == InvoiceStatus.CANCELLED
        )
        .count()
    )
    average_order = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )
    return {
        "total_revenue": round(float(total_revenue), 2),
        "total_orders": int(total_orders),
        "successful_orders": int(successful_orders),
        "cancelled_orders": int(cancelled_orders),
        "average_order_value": round(
            float(average_order),
            2
        ),
    }



def get_top_products(db, limit: int = 10):

    rows = (
        db.query(
            Product.name,
            Product.category,
            func.sum(CartItem.quantity).label("quantity_sold"),
            func.sum(
                CartItem.quantity * CartItem.unit_price
            ).label("revenue")
        )
        .join(
            CartItem,
            Product.id == CartItem.product_id
        )
        .group_by(
            Product.id,
            Product.name,
            Product.category
        )
        .order_by(
            func.sum(CartItem.quantity).desc()
        )
        .limit(limit)
        .all()
    )

    results = []

    for i, row in enumerate(rows, start=1):

        results.append(
            {
                "rank": i,
                "product": row.name,
                "category": row.category,
                "quantity_sold": int(row.quantity_sold),
                "revenue": round(float(row.revenue), 2),
            }
        )

    return results

def get_inventory_overview(db):

    total_products = db.query(Product).count()

    inventory_value = (
        db.query(
            func.coalesce(
                func.sum(Product.price * Product.quantity),
                0.0
            )
        ).scalar() or 0.0
    )

    out_of_stock = (
        db.query(Product)
        .filter(Product.quantity == 0)
        .count()
    )

    low_stock = (
        db.query(Product)
        .filter(
            Product.quantity > 0,
            Product.quantity <= 10
        )
        .count()
    )

    healthy_inventory = (
        db.query(Product)
        .filter(Product.quantity > 10)
        .count()
    )

    return {
        "total_products": int(total_products),
        "inventory_value": float(round(inventory_value, 2)),
        "healthy_inventory": int(healthy_inventory),
        "low_stock": int(low_stock),
        "out_of_stock": int(out_of_stock),
    }



def get_product_performance(db, limit: int = 50):

    rows = (
        db.query(
            Product.id,
            Product.name,
            Product.category,
            Product.quantity,
            Product.price,
            func.coalesce(
                func.sum(CartItem.quantity),
                0
            ).label("quantity_sold"),
            func.coalesce(
                func.sum(
                    CartItem.quantity * CartItem.unit_price
                ),
                0
            ).label("revenue"),
        )
        .outerjoin(
            CartItem,
            Product.id == CartItem.product_id
        )
        .group_by(
            Product.id,
            Product.name,
            Product.category,
            Product.quantity,
            Product.price,
        )
        .order_by(
            func.coalesce(
                func.sum(CartItem.quantity),
                0
            ).desc()
        )
        .limit(limit)
        .all()
    )

    results = []

    for row in rows:

        current_stock = int(row.quantity or 0)
        quantity_sold = int(row.quantity_sold or 0)
        revenue = float(row.revenue or 0)

        # -------------------------
        # Stock status
        # -------------------------

        if current_stock == 0:
            stock_status = "Out of Stock"

        elif current_stock <= 10:
            stock_status = "Critical"

        elif current_stock <= 25:
            stock_status = "Low"

        else:
            stock_status = "Healthy"

        # -------------------------
        # Sales status
        # -------------------------

        if quantity_sold == 0:
            sales_status = "No Sales"

        elif quantity_sold >= 5:
            sales_status = "Best Seller"

        elif quantity_sold >= 2:
            sales_status = "Selling"

        else:
            sales_status = "Slow Seller"

        # -------------------------
        # Calculations
        # -------------------------

        inventory_value = current_stock * float(row.price or 0)

        average_selling_price = (
            revenue / quantity_sold
            if quantity_sold > 0
            else 0
        )

        results.append({
            "id": int(row.id),
            "product": row.name,
            "category": row.category,

            "current_stock": current_stock,

            "quantity_sold": quantity_sold,
            "revenue": round(revenue, 2),

            "inventory_value": round(
                inventory_value,
                2
            ),

            "average_selling_price": round(
                average_selling_price,
                2
            ),

            "stock_status": stock_status,
            "sales_status": sales_status,
        })

    return results


def get_category_performance(db):

    rows = (
        db.query(
            Product.category,
            func.count(Product.id).label("products"),
            func.coalesce(
                func.sum(CartItem.quantity),
                0
            ).label("quantity_sold"),
            func.coalesce(
                func.sum(
                    CartItem.quantity * CartItem.unit_price
                ),
                0
            ).label("revenue"),
        )
        .outerjoin(
            CartItem,
            Product.id == CartItem.product_id
        )
        .group_by(
            Product.category
        )
        .order_by(
            func.coalesce(
                func.sum(
                    CartItem.quantity * CartItem.unit_price
                ),
                0
            ).desc()
        )
        .all()
    )

    total_revenue = sum(
        float(row.revenue or 0)
        for row in rows
    )

    results = []

    for row in rows:
        revenue = float(row.revenue or 0)
        percentage = (
            (revenue / total_revenue) * 100
            if total_revenue > 0
            else 0
        )
        results.append({
            "category": row.category or "Unknown",
            "products": int(row.products or 0),
            "quantity_sold": int(row.quantity_sold or 0),
            "revenue": round(revenue, 2),
            "percentage_of_sales": round(
                percentage,
                2
            ),
        })

    return results


def get_inventory_alerts(db):

    rows = (
        db.query(
            Product.id,
            Product.name,
            Product.category,
            Product.quantity,
            Product.price,
            func.coalesce(
                func.sum(CartItem.quantity),
                0
            ).label("quantity_sold"),
            func.coalesce(
                func.sum(
                    CartItem.quantity * CartItem.unit_price
                ),
                0
            ).label("revenue"),
        )
        .outerjoin(
            CartItem,
            Product.id == CartItem.product_id
        )
        .group_by(
            Product.id,
            Product.name,
            Product.category,
            Product.quantity,
            Product.price,
        )
        .all()
    )

    # Separate results by alert type/priority
    out_of_stock_alerts = []
    critical_stock_alerts = []
    low_stock_alerts = []
    no_sales_alerts = []
    slow_seller_alerts = []

    for row in rows:
        current_stock = int(row.quantity or 0)
        quantity_sold = int(row.quantity_sold or 0)
        revenue = float(row.revenue or 0)

        # Determine alert type and message
        # Priority hierarchy (highest to lowest)
        if current_stock == 0:
            alert_type = "OUT_OF_STOCK"
            message = f"{row.name} is out of stock"
            out_of_stock_alerts.append({
                "id": int(row.id),
                "product": row.name,
                "category": row.category,
                "current_stock": current_stock,
                "quantity_sold": quantity_sold,
                "revenue": round(revenue, 2),
                "alert_type": alert_type,
                "message": message,
            })

        elif current_stock <= 10:
            alert_type = "CRITICAL_STOCK"
            message = f"{row.name} has critical stock (only {current_stock} units)"
            critical_stock_alerts.append({
                "id": int(row.id),
                "product": row.name,
                "category": row.category,
                "current_stock": current_stock,
                "quantity_sold": quantity_sold,
                "revenue": round(revenue, 2),
                "alert_type": alert_type,
                "message": message,
            })

        elif current_stock <= 25:
            alert_type = "LOW_STOCK"
            message = f"{row.name} has low stock ({current_stock} units)"
            low_stock_alerts.append({
                "id": int(row.id),
                "product": row.name,
                "category": row.category,
                "current_stock": current_stock,
                "quantity_sold": quantity_sold,
                "revenue": round(revenue, 2),
                "alert_type": alert_type,
                "message": message,
            })

        elif quantity_sold == 0:
            alert_type = "NO_SALES"
            message = f"{row.name} has no sales in the period"
            no_sales_alerts.append({
                "id": int(row.id),
                "product": row.name,
                "category": row.category,
                "current_stock": current_stock,
                "quantity_sold": quantity_sold,
                "revenue": round(revenue, 2),
                "alert_type": alert_type,
                "message": message,
            })

        elif quantity_sold == 1:
            alert_type = "SLOW_SELLER"
            message = f"{row.name} is selling slowly"
            slow_seller_alerts.append({
                "id": int(row.id),
                "product": row.name,
                "category": row.category,
                "current_stock": current_stock,
                "quantity_sold": quantity_sold,
                "revenue": round(revenue, 2),
                "alert_type": alert_type,
                "message": message,
            })

    # Combine results: keep all critical alerts, limit low-priority ones
    results = []
    results.extend(out_of_stock_alerts)
    results.extend(critical_stock_alerts)
    results.extend(low_stock_alerts)
    results.extend(no_sales_alerts[:10])  # Limit to top 10
    results.extend(slow_seller_alerts[:10])  # Limit to top 10

    return results