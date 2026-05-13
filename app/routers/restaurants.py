from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Restaurant
from app.schemas import RestaurantCreate, RestaurantOut, RestaurantUpdate
from app.security import AdminUser

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantOut])
def list_restaurants(db: Session = Depends(get_db), open_only: bool = False) -> list[Restaurant]:
    q = db.query(Restaurant)
    if open_only:
        q = q.filter(Restaurant.is_open.is_(True))
    return q.order_by(Restaurant.id).all()


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)) -> Restaurant:
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return r


@router.post("", response_model=RestaurantOut, status_code=201)
def create_restaurant(
    _admin: AdminUser,
    payload: RestaurantCreate,
    db: Session = Depends(get_db),
) -> Restaurant:
    r = Restaurant(name=payload.name, address=payload.address, is_open=payload.is_open)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{restaurant_id}", response_model=RestaurantOut)
def update_restaurant(
    restaurant_id: int,
    _admin: AdminUser,
    payload: RestaurantUpdate,
    db: Session = Depends(get_db),
) -> Restaurant:
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{restaurant_id}", status_code=204)
def delete_restaurant(
    restaurant_id: int,
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> None:
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    db.delete(r)
    db.commit()
