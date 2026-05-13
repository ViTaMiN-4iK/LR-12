from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Order, User
from app.schemas import OrderOut, UserOut
from app.security import AdminUser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(_admin: AdminUser, db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, admin: AdminUser, db: Session = Depends(get_db)) -> User:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = False
    db.commit()
    db.refresh(u)
    return u


@router.get("/orders", response_model=list[OrderOut])
def all_orders(_admin: AdminUser, db: Session = Depends(get_db)) -> list[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.events))
        .order_by(Order.id.desc())
        .all()
    )
