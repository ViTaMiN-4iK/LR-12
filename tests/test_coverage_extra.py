"""Additional API coverage for lab (goal: >=90% on app)."""

import pytest
from fastapi.testclient import TestClient

from app.models import User, UserRole
from app.security import hash_password


@pytest.fixture
def admin_user(db_session):
    u = User(
        email="admin@test.com",
        hashed_password=hash_password("adminadmin"),
        full_name="Admin",
        role=UserRole.admin,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def customer_user(db_session):
    u = User(
        email="cust@test.com",
        hashed_password=hash_password("custcust1"),
        full_name="Customer",
        role=UserRole.customer,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _tok(c: TestClient, e: str, p: str) -> str:
    return c.post("/auth/login", data={"username": e, "password": p}).json()["access_token"]


def test_unauthorized(client: TestClient):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/restaurants", json={"name": "x", "address": "y"}).status_code == 401


def test_register_duplicate(client: TestClient, admin_user):
    assert (
        client.post(
            "/auth/register",
            json={"email": "admin@test.com", "password": "x" * 9, "full_name": "X"},
        ).status_code
        == 400
    )


def test_login_bad_password(client: TestClient, admin_user):
    assert client.post("/auth/login", data={"username": "admin@test.com", "password": "wrong"}).status_code == 401


def test_restaurants_list_filters(client: TestClient, admin_user):
    h = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    client.post("/restaurants", json={"name": "Open", "address": "1"}, headers=h)
    rid2 = client.post("/restaurants", json={"name": "Closed", "address": "2"}, headers=h).json()["id"]
    client.put(f"/restaurants/{rid2}", json={"is_open": False}, headers=h)
    all_r = client.get("/restaurants").json()
    assert len(all_r) >= 2
    open_r = client.get("/restaurants?open_only=true").json()
    assert all(x["is_open"] for x in open_r)


def test_dish_crud_and_get(client: TestClient, admin_user):
    h = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    rid = client.post("/restaurants", json={"name": "R", "address": "A"}, headers=h).json()["id"]
    did = client.post(f"/restaurants/{rid}/dishes", json={"name": "D", "price": "2.00"}, headers=h).json()["id"]
    g = client.get(f"/restaurants/{rid}/dishes/{did}")
    assert g.json()["name"] == "D"
    client.put(f"/restaurants/{rid}/dishes/{did}", json={"name": "D2"}, headers=h)
    assert client.get(f"/restaurants/{rid}/dishes/{did}").json()["name"] == "D2"
    client.delete(f"/restaurants/{rid}/dishes/{did}", headers=h)
    assert client.get(f"/restaurants/{rid}/dishes/{did}").status_code == 404


def test_courier_update_delete(client: TestClient, admin_user):
    h = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    cp = client.post(
        "/couriers",
        json={"email": "c1@test.com", "password": "cccccccc1", "full_name": "C1", "vehicle_info": "v"},
        headers=h,
    ).json()
    cid = cp["id"]
    client.put(f"/couriers/{cid}", json={"vehicle_info": "bike", "is_available": False}, headers=h)
    assert client.get("/couriers", headers=h).json()[0]["vehicle_info"] == "bike"
    client.delete(f"/couriers/{cid}", headers=h)
    assert client.get("/couriers", headers=h).json() == []


def test_admin_users_orders(client: TestClient, admin_user, customer_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    users = client.get("/admin/users", headers=ah).json()
    assert len(users) >= 2
    cid = next(u["id"] for u in users if u["email"] == "cust@test.com")
    assert client.patch(f"/admin/users/{cid}/deactivate", headers=ah).status_code == 200
    assert client.post("/auth/login", data={"username": "cust@test.com", "password": "custcust1"}).status_code == 403


def test_admin_cannot_deactivate_self(client: TestClient, admin_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    aid = client.get("/auth/me", headers=ah).json()["id"]
    assert client.patch(f"/admin/users/{aid}/deactivate", headers=ah).status_code == 400


def test_customer_cancel(client: TestClient, admin_user, customer_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    ch = {"Authorization": f"Bearer {_tok(client, 'cust@test.com', 'custcust1')}"}
    rid = client.post("/restaurants", json={"name": "Rx", "address": "Ax"}, headers=ah).json()["id"]
    did = client.post(f"/restaurants/{rid}/dishes", json={"name": "Dx", "price": "1"}, headers=ah).json()["id"]
    oid = client.post(
        "/orders", json={"restaurant_id": rid, "items": [{"dish_id": did, "quantity": 1}]}, headers=ch
    ).json()["id"]
    assert (
        client.patch(f"/orders/{oid}/status", json={"status": "cancelled"}, headers=ch).status_code == 200
    )


def test_order_wrong_dish_restaurant(client: TestClient, admin_user, customer_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    ch = {"Authorization": f"Bearer {_tok(client, 'cust@test.com', 'custcust1')}"}
    r1 = client.post("/restaurants", json={"name": "A", "address": "a"}, headers=ah).json()["id"]
    r2 = client.post("/restaurants", json={"name": "B", "address": "b"}, headers=ah).json()["id"]
    d2 = client.post(f"/restaurants/{r2}/dishes", json={"name": "onlyB", "price": "1"}, headers=ah).json()["id"]
    bad = client.post(
        "/orders",
        json={"restaurant_id": r1, "items": [{"dish_id": d2, "quantity": 1}]},
        headers=ch,
    )
    assert bad.status_code == 422


def test_admin_my_orders_bad(client: TestClient, admin_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    assert client.get("/orders/mine", headers=ah).status_code == 400


def test_reports_date_filters(client: TestClient, admin_user, customer_user):
    ah = {"Authorization": f"Bearer {_tok(client, 'admin@test.com', 'adminadmin')}"}
    ch = {"Authorization": f"Bearer {_tok(client, 'cust@test.com', 'custcust1')}"}
    rid = client.post("/restaurants", json={"name": "Rz", "address": "z"}, headers=ah).json()["id"]
    did = client.post(f"/restaurants/{rid}/dishes", json={"name": "Z", "price": "1"}, headers=ah).json()["id"]
    cpid = client.post(
        "/couriers",
        json={"email": "cz@test.com", "password": "czczczcz1", "full_name": "Zc", "vehicle_info": ""},
        headers=ah,
    ).json()["id"]
    oid = client.post(
        "/orders", json={"restaurant_id": rid, "items": [{"dish_id": did, "quantity": 1}]}, headers=ch
    ).json()["id"]
    for st in ["confirmed", "preparing", "ready_for_pickup"]:
        client.patch(f"/orders/{oid}/status", json={"status": st}, headers=ah)
    client.post(f"/orders/{oid}/assign-courier", json={"courier_profile_id": cpid}, headers=ah)
    ct = {"Authorization": f"Bearer {_tok(client, 'cz@test.com', 'czczczcz1')}"}
    client.patch(f"/orders/{oid}/status", json={"status": "out_for_delivery"}, headers=ct)
    client.patch(f"/orders/{oid}/status", json={"status": "delivered"}, headers=ct)
    r = client.get("/reports/top-dishes?start=2099-01-01", headers=ah)
    assert r.status_code == 200
    assert r.json() == []
    r2 = client.get("/reports/courier-load?start=2099-01-01", headers=ah)
    assert r2.status_code == 200
