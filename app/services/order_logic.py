from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Dish, Order, OrderItem, OrderStatus, OrderTrackingEvent, UserRole


ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.pending: frozenset({OrderStatus.confirmed, OrderStatus.cancelled}),
    OrderStatus.confirmed: frozenset({OrderStatus.preparing, OrderStatus.cancelled}),
    OrderStatus.preparing: frozenset({OrderStatus.ready_for_pickup, OrderStatus.cancelled}),
    OrderStatus.ready_for_pickup: frozenset({OrderStatus.out_for_delivery, OrderStatus.cancelled}),
    OrderStatus.out_for_delivery: frozenset({OrderStatus.delivered}),
    OrderStatus.delivered: frozenset(),
    OrderStatus.cancelled: frozenset(),
}


def can_transition(current: OrderStatus, new: OrderStatus) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, frozenset())


def compute_order_total(db: Session, restaurant_id: int, items: list[tuple[int, int]]) -> tuple[Decimal, list[tuple[Dish, int]]]:
    """Returns total and list of (dish, quantity). Raises ValueError on invalid data."""
    total = Decimal("0.00")
    resolved: list[tuple[Dish, int]] = []
    for dish_id, qty in items:
        dish = db.query(Dish).filter(Dish.id == dish_id).first()
        if dish is None:
            raise ValueError(f"Dish {dish_id} not found")
        if dish.restaurant_id != restaurant_id:
            raise ValueError("All dishes must belong to the selected restaurant")
        if not dish.is_available:
            raise ValueError(f"Dish {dish_id} is not available")
        total += dish.price * qty
        resolved.append((dish, qty))
    return total.quantize(Decimal("0.01")), resolved


def append_tracking(db: Session, order: Order, status: OrderStatus, note: str | None) -> None:
    ev = OrderTrackingEvent(order_id=order.id, status=status, location_note=note)
    db.add(ev)


def user_may_update_status(user_role: UserRole, order: Order, new_status: OrderStatus) -> bool:
    if user_role == UserRole.admin:
        return can_transition(order.status, new_status)
    if user_role == UserRole.customer:
        return new_status == OrderStatus.cancelled and order.status in (
            OrderStatus.pending,
            OrderStatus.confirmed,
        )
    if user_role == UserRole.courier:
        if order.courier_id is None:
            return False
        # courier user must match order.courier user_id - checked in route
        return new_status in (OrderStatus.out_for_delivery, OrderStatus.delivered) and can_transition(
            order.status, new_status
        )
    return False
