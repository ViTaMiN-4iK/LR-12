from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import CourierProfile, Order, OrderItem, OrderStatus, User, UserRole
from app.schemas import AssignCourierBody, OrderCreate, OrderOut, OrderStatusUpdate
from app.security import AdminUser, CurrentUser
from app.services.order_logic import (
    append_tracking,
    can_transition,
    compute_order_total,
    user_may_update_status,
)

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_out(order: Order) -> Order:
    order.items  # noqa: B018
    order.events
    return order


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    user: CurrentUser,
    payload: OrderCreate,
    db: Session = Depends(get_db),
) -> Order:
    if user.role not in (UserRole.customer, UserRole.admin):
        raise HTTPException(status_code=403, detail="Only customers can create orders")
    pairs = [(i.dish_id, i.quantity) for i in payload.items]
    try:
        total, resolved = compute_order_total(db, payload.restaurant_id, pairs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    order = Order(
        customer_id=user.id,
        restaurant_id=payload.restaurant_id,
        status=OrderStatus.pending,
        total_amount=total,
    )
    db.add(order)
    db.flush()
    for dish, qty in resolved:
        db.add(
            OrderItem(
                order_id=order.id,
                dish_id=dish.id,
                quantity=qty,
                unit_price=dish.price,
            )
        )
    append_tracking(db, order, OrderStatus.pending, "Order created")
    db.commit()
    db.refresh(order)
    return _order_out(
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.events))
        .filter(Order.id == order.id)
        .first()
    )


@router.get("/mine", response_model=list[OrderOut])
def my_orders(user: CurrentUser, db: Session = Depends(get_db)) -> list[Order]:
    if user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Use /admin/orders for admin")
    q = db.query(Order).options(joinedload(Order.items), joinedload(Order.events))
    if user.role == UserRole.customer:
        q = q.filter(Order.customer_id == user.id)
    elif user.role == UserRole.courier:
        cp = db.query(CourierProfile).filter(CourierProfile.user_id == user.id).first()
        if cp is None:
            return []
        q = q.filter(Order.courier_id == cp.id)
    return q.order_by(Order.id.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(user: CurrentUser, order_id: int, db: Session = Depends(get_db)) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.events))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == UserRole.admin:
        return order
    if user.role == UserRole.customer and order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role == UserRole.courier:
        cp = db.query(CourierProfile).filter(CourierProfile.user_id == user.id).first()
        if cp is None or order.courier_id != cp.id:
            raise HTTPException(status_code=403, detail="Forbidden")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_status(
    user: CurrentUser,
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    new_status = OrderStatus(body.status.value)

    if user.role == UserRole.courier:
        cp = db.query(CourierProfile).filter(CourierProfile.user_id == user.id).first()
        if cp is None or order.courier_id != cp.id:
            raise HTTPException(status_code=403, detail="Courier not assigned to this order")
        if not user_may_update_status(user.role, order, new_status):
            raise HTTPException(status_code=403, detail="Not allowed for this status transition")
    elif user.role == UserRole.customer:
        if order.customer_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if not user_may_update_status(user.role, order, new_status):
            raise HTTPException(status_code=403, detail="Customers can only cancel early-stage orders")
    elif user.role == UserRole.admin:
        if not can_transition(order.status, new_status):
            raise HTTPException(status_code=422, detail=f"Invalid transition {order.status} -> {new_status}")
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    order.status = new_status
    if new_status == OrderStatus.delivered:
        order.delivered_at = datetime.now(timezone.utc)
    append_tracking(db, order, new_status, body.location_note)
    db.commit()
    return (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.events))
        .filter(Order.id == order_id)
        .first()
    )


@router.post("/{order_id}/assign-courier", response_model=OrderOut)
def assign_courier(
    order_id: int,
    _admin: AdminUser,
    body: AssignCourierBody,
    db: Session = Depends(get_db),
) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    cp = db.query(CourierProfile).filter(CourierProfile.id == body.courier_profile_id).first()
    if cp is None:
        raise HTTPException(status_code=404, detail="Courier profile not found")
    order.courier_id = cp.id
    db.commit()
    return (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.events))
        .filter(Order.id == order_id)
        .first()
    )
