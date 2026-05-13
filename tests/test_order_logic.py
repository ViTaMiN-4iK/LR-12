"""Unit tests for order transition rules (no HTTP)."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Dish, OrderStatus, Restaurant, User, UserRole
from app.services.order_logic import can_transition, compute_order_total, user_may_update_status


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_can_transition_chain():
    assert can_transition(OrderStatus.pending, OrderStatus.confirmed)
    assert can_transition(OrderStatus.pending, OrderStatus.cancelled)
    assert not can_transition(OrderStatus.pending, OrderStatus.delivered)
    assert can_transition(OrderStatus.out_for_delivery, OrderStatus.delivered)
    assert not can_transition(OrderStatus.delivered, OrderStatus.pending)


def test_user_may_update_status_roles():
    class O:
        status = OrderStatus.pending
        courier_id = 1

    o = O()
    assert user_may_update_status(UserRole.customer, o, OrderStatus.cancelled)
    assert not user_may_update_status(UserRole.customer, o, OrderStatus.confirmed)
    assert user_may_update_status(UserRole.admin, o, OrderStatus.confirmed)
    o2 = O()
    o2.status = OrderStatus.ready_for_pickup
    o2.courier_id = 5
    assert user_may_update_status(UserRole.courier, o2, OrderStatus.out_for_delivery)
    assert not user_may_update_status(UserRole.courier, o2, OrderStatus.cancelled)


def test_compute_order_total(memory_db):
    db = memory_db
    r = Restaurant(name="R", address="a")
    db.add(r)
    db.flush()
    d = Dish(restaurant_id=r.id, name="x", price=Decimal("3.50"), is_available=True)
    db.add(d)
    db.commit()
    total, resolved = compute_order_total(db, r.id, [(d.id, 2)])
    assert total == Decimal("7.00")
    assert len(resolved) == 1
    with pytest.raises(ValueError, match="not found"):
        compute_order_total(db, r.id, [(999, 1)])
    r2 = Restaurant(name="R2", address="b")
    db.add(r2)
    db.flush()
    d2 = Dish(restaurant_id=r2.id, name="y", price=Decimal("1"), is_available=True)
    db.add(d2)
    db.commit()
    with pytest.raises(ValueError, match="belong"):
        compute_order_total(db, r.id, [(d2.id, 1)])
    d.is_available = False
    db.commit()
    with pytest.raises(ValueError, match="not available"):
        compute_order_total(db, r.id, [(d.id, 1)])
