from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CourierProfile, Dish, Order, OrderItem, OrderStatus, Restaurant, User
from app.schemas import CourierLoadRow, TopDishRow
from app.security import AdminUser

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/top-dishes", response_model=list[TopDishRow])
def top_dishes(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[TopDishRow]:
    """Top dishes by units sold for delivered orders in date range."""
    stmt = (
        select(
            Dish.id.label("dish_id"),
            Dish.name.label("dish_name"),
            Restaurant.id.label("restaurant_id"),
            Restaurant.name.label("restaurant_name"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price), 0).label("revenue"),
        )
        .join(OrderItem, OrderItem.dish_id == Dish.id)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Restaurant, Restaurant.id == Dish.restaurant_id)
        .where(Order.status == OrderStatus.delivered)
    )
    if start is not None:
        stmt = stmt.where(func.date(Order.created_at) >= start)
    if end is not None:
        stmt = stmt.where(func.date(Order.created_at) <= end)
    stmt = stmt.group_by(Dish.id, Dish.name, Restaurant.id, Restaurant.name).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(limit)
    rows = db.execute(stmt).all()
    return [
        TopDishRow(
            dish_id=r.dish_id,
            dish_name=r.dish_name,
            restaurant_id=r.restaurant_id,
            restaurant_name=r.restaurant_name,
            units_sold=int(r.units_sold or 0),
            revenue=Decimal(r.revenue or 0).quantize(Decimal("0.01")),
        )
        for r in rows
    ]


@router.get("/courier-load", response_model=list[CourierLoadRow])
def courier_load(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
) -> list[CourierLoadRow]:
    stmt = (
        select(
            CourierProfile.id.label("courier_profile_id"),
            User.full_name.label("courier_name"),
            func.count(Order.id).label("orders_delivered"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
        )
        .select_from(CourierProfile)
        .join(User, User.id == CourierProfile.user_id)
        .join(Order, Order.courier_id == CourierProfile.id)
        .where(Order.status == OrderStatus.delivered)
        .group_by(CourierProfile.id, User.full_name)
    )
    if start is not None:
        stmt = stmt.where(func.date(Order.delivered_at) >= start)
    if end is not None:
        stmt = stmt.where(func.date(Order.delivered_at) <= end)
    rows = db.execute(stmt).all()
    return [
        CourierLoadRow(
            courier_profile_id=r.courier_profile_id,
            courier_name=r.courier_name,
            orders_delivered=int(r.orders_delivered or 0),
            total_revenue=Decimal(r.total_revenue or 0).quantize(Decimal("0.01")),
        )
        for r in rows
    ]
