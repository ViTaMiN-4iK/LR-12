from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dish, Restaurant
from app.schemas import DishCreate, DishOut, DishUpdate
from app.security import AdminUser

router = APIRouter(prefix="/restaurants/{restaurant_id}/dishes", tags=["dishes"])


def _get_restaurant(db: Session, restaurant_id: int) -> Restaurant:
    r = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return r


@router.get("", response_model=list[DishOut])
def list_dishes(restaurant_id: int, db: Session = Depends(get_db)) -> list[Dish]:
    _get_restaurant(db, restaurant_id)
    return db.query(Dish).filter(Dish.restaurant_id == restaurant_id).order_by(Dish.id).all()


@router.post("", response_model=DishOut, status_code=201)
def create_dish(
    restaurant_id: int,
    _admin: AdminUser,
    payload: DishCreate,
    db: Session = Depends(get_db),
) -> Dish:
    _get_restaurant(db, restaurant_id)
    d = Dish(
        restaurant_id=restaurant_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        is_available=payload.is_available,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.get("/{dish_id}", response_model=DishOut)
def get_dish(restaurant_id: int, dish_id: int, db: Session = Depends(get_db)) -> Dish:
    _get_restaurant(db, restaurant_id)
    d = db.query(Dish).filter(Dish.id == dish_id, Dish.restaurant_id == restaurant_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    return d


@router.put("/{dish_id}", response_model=DishOut)
def update_dish(
    restaurant_id: int,
    dish_id: int,
    _admin: AdminUser,
    payload: DishUpdate,
    db: Session = Depends(get_db),
) -> Dish:
    _get_restaurant(db, restaurant_id)
    d = db.query(Dish).filter(Dish.id == dish_id, Dish.restaurant_id == restaurant_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/{dish_id}", status_code=204)
def delete_dish(
    restaurant_id: int,
    dish_id: int,
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> None:
    _get_restaurant(db, restaurant_id)
    d = db.query(Dish).filter(Dish.id == dish_id, Dish.restaurant_id == restaurant_id).first()
    if d is None:
        raise HTTPException(status_code=404, detail="Dish not found")
    db.delete(d)
    db.commit()
