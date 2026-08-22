from pydantic import BaseModel


class SalesOverview(BaseModel):
    total_revenue: float
    total_orders: int
    successful_orders: int
    cancelled_orders: int
    average_order_value: float


class TopProduct(BaseModel):
    rank: int
    product: str
    category: str | None
    quantity_sold: int
    revenue: float


class InventoryOverview(BaseModel):
    total_products: int
    inventory_value: float
    healthy_inventory: int
    low_stock: int
    out_of_stock: int


class ProductPerformance(BaseModel):
    id: int
    product: str
    category: str | None

    current_stock: int

    quantity_sold: int
    revenue: float

    inventory_value: float
    average_selling_price: float

    stock_status: str
    sales_status: str


class CategoryPerformance(BaseModel):
    category: str
    products: int
    quantity_sold: int
    revenue: float
    percentage_of_sales: float


class InventoryAlert(BaseModel):
    id: int
    product: str
    category: str | None
    current_stock: int
    quantity_sold: int
    revenue: float
    alert_type: str
    message: str


class SalesTrend(BaseModel):
    date: str
    orders: int
    quantity_sold: int
    revenue: float


class BusinessInsight(BaseModel):
    type: str
    severity: str
    title: str
    message: str