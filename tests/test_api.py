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


def _token(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_health(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_me(client: TestClient):
    r = client.post(
        "/auth/register",
        json={"email": "u@u.com", "password": "password1", "full_name": "U"},
    )
    assert r.status_code == 201
    tok = _token(client, "u@u.com", "password1")
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["email"] == "u@u.com"


def test_restaurant_crud_admin(client: TestClient, admin_user):
    t = _token(client, "admin@test.com", "adminadmin")
    h = {"Authorization": f"Bearer {t}"}
    r = client.post("/restaurants", json={"name": "R1", "address": "Addr 1"}, headers=h)
    assert r.status_code == 201
    rid = r.json()["id"]
    g = client.get(f"/restaurants/{rid}")
    assert g.json()["name"] == "R1"
    u = client.put(f"/restaurants/{rid}", json={"is_open": False}, headers=h)
    assert u.json()["is_open"] is False


def test_dish_and_order_flow(client: TestClient, admin_user, customer_user):
    admin_t = _token(client, "admin@test.com", "adminadmin")
    cust_t = _token(client, "cust@test.com", "custcust1")
    ah = {"Authorization": f"Bearer {admin_t}"}
    ch = {"Authorization": f"Bearer {cust_t}"}

    r = client.post("/restaurants", json={"name": "Pizza", "address": "Main 1"}, headers=ah)
    rid = r.json()["id"]
    d = client.post(
        f"/restaurants/{rid}/dishes",
        json={"name": "Margherita", "price": "9.99", "description": "cheese"},
        headers=ah,
    )
    assert d.status_code == 201
    did = d.json()["id"]

    o = client.post(
        "/orders",
        json={"restaurant_id": rid, "items": [{"dish_id": did, "quantity": 2}]},
        headers=ch,
    )
    assert o.status_code == 201
    oid = o.json()["id"]
    assert o.json()["status"] == "pending"
    assert float(o.json()["total_amount"]) == pytest.approx(19.98)

    # admin advances status chain
    for st in ["confirmed", "preparing", "ready_for_pickup"]:
        p = client.patch(f"/orders/{oid}/status", json={"status": st}, headers=ah)
        assert p.status_code == 200, p.text

    # create courier
    cr = client.post(
        "/couriers",
        json={
            "email": "cour@test.com",
            "password": "courcour1",
            "full_name": "Courier",
            "vehicle_info": "bike",
        },
        headers=ah,
    )
    assert cr.status_code == 201
    cpid = cr.json()["id"]
    client.post(f"/orders/{oid}/assign-courier", json={"courier_profile_id": cpid}, headers=ah)

    cour_t = _token(client, "cour@test.com", "courcour1")
    coh = {"Authorization": f"Bearer {cour_t}"}
    p = client.patch(
        "/orders/" + str(oid) + "/status",
        json={"status": "out_for_delivery", "location_note": "on the way"},
        headers=coh,
    )
    assert p.status_code == 200
    p2 = client.patch("/orders/" + str(oid) + "/status", json={"status": "delivered"}, headers=coh)
    assert p2.status_code == 200


def test_reports_top_dishes_and_courier_load(client: TestClient, admin_user, customer_user):
    admin_t = _token(client, "admin@test.com", "adminadmin")
    cust_t = _token(client, "cust@test.com", "custcust1")
    ah = {"Authorization": f"Bearer {admin_t}"}
    ch = {"Authorization": f"Bearer {cust_t}"}
    rid = client.post("/restaurants", json={"name": "R", "address": "A"}, headers=ah).json()["id"]
    did = client.post(
        f"/restaurants/{rid}/dishes",
        json={"name": "Soup", "price": "5.00"},
        headers=ah,
    ).json()["id"]
    cpid = client.post(
        "/couriers",
        json={
            "email": "rep@test.com",
            "password": "reprep123",
            "full_name": "Courier Rep",
            "vehicle_info": "bike",
        },
        headers=ah,
    ).json()["id"]
    oid = client.post(
        "/orders",
        json={"restaurant_id": rid, "items": [{"dish_id": did, "quantity": 2}]},
        headers=ch,
    ).json()["id"]
    for st in ["confirmed", "preparing", "ready_for_pickup"]:
        assert client.patch(f"/orders/{oid}/status", json={"status": st}, headers=ah).status_code == 200
    assert client.post(f"/orders/{oid}/assign-courier", json={"courier_profile_id": cpid}, headers=ah).status_code == 200
    ct = _token(client, "rep@test.com", "reprep123")
    coh = {"Authorization": f"Bearer {ct}"}
    assert client.patch(f"/orders/{oid}/status", json={"status": "out_for_delivery"}, headers=coh).status_code == 200
    assert client.patch(f"/orders/{oid}/status", json={"status": "delivered"}, headers=coh).status_code == 200
    rep = client.get("/reports/top-dishes", headers=ah)
    assert rep.status_code == 200
    assert any(row["dish_name"] == "Soup" for row in rep.json())
    cl = client.get("/reports/courier-load", headers=ah)
    assert cl.status_code == 200
    assert len(cl.json()) >= 1


def test_invalid_transition(client: TestClient, admin_user, customer_user):
    admin_t = _token(client, "admin@test.com", "adminadmin")
    cust_t = _token(client, "cust@test.com", "custcust1")
    ah = {"Authorization": f"Bearer {admin_t}"}
    ch = {"Authorization": f"Bearer {cust_t}"}
    rid = client.post("/restaurants", json={"name": "R2", "address": "A"}, headers=ah).json()["id"]
    did = client.post(
        f"/restaurants/{rid}/dishes",
        json={"name": "D", "price": "1.00"},
        headers=ah,
    ).json()["id"]
    oid = client.post(
        "/orders",
        json={"restaurant_id": rid, "items": [{"dish_id": did, "quantity": 1}]},
        headers=ch,
    ).json()["id"]
    bad = client.patch("/orders/" + str(oid) + "/status", json={"status": "delivered"}, headers=ah)
    assert bad.status_code == 422
