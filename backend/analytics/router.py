from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from core.database import get_db
from analytics.service import AnalyticsService
from analytics.schemas import (
    SalesOverview,
    TopProduct,
    InventoryOverview,
    ProductPerformance,
    CategoryPerformance,
    InventoryAlert,
    SalesTrend,
    BusinessInsight,
)

from typing import List

router = APIRouter()


@router.get(
    "/sales",
    response_model=SalesOverview
)
def sales_dashboard(
    db: Session = Depends(get_db)
):

    return AnalyticsService.sales_overview(db)


@router.get(
    "/top-products",
    response_model=List[TopProduct]
)
def top_products(
    limit: int = 10,
    db: Session = Depends(get_db)
):

    return AnalyticsService.top_products(
        db,
        limit
    )

@router.get(
    "/inventory",
    response_model=InventoryOverview
)
def inventory_dashboard(
    db: Session = Depends(get_db)
):

    return AnalyticsService.inventory_overview(db)

@router.get(
    "/product-performance",
    response_model=List[ProductPerformance]
)
def product_performance(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return AnalyticsService.product_performance(
        db,
        limit
    )

@router.get(
    "/category-performance",
    response_model=List[CategoryPerformance]
)
def category_performance(
    db: Session = Depends(get_db)
):
    return AnalyticsService.category_performance(db)

@router.get(
    "/inventory-alerts",
    response_model=List[InventoryAlert]
)
def inventory_alerts(
    db: Session = Depends(get_db)
):
    return AnalyticsService.inventory_alerts(db)


@router.get(
    "/sales-trends",
    response_model=List[SalesTrend]
)
def sales_trends(
    days: int = 30,
    db: Session = Depends(get_db)
):
    return AnalyticsService.sales_trends(db, days)


@router.get(
    "/insights",
    response_model=List[BusinessInsight]
)
def business_insights(
    db: Session = Depends(get_db)
):
    return AnalyticsService.business_insights(db)


