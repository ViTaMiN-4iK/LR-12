from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import CourierProfile, User, UserRole
from app.schemas import CourierCreate, CourierOut, CourierUpdate
from app.security import AdminUser, hash_password

router = APIRouter(prefix="/couriers", tags=["couriers"])


@router.get("", response_model=list[CourierOut])
def list_couriers(_admin: AdminUser, db: Session = Depends(get_db)) -> list[CourierProfile]:
    return db.query(CourierProfile).options(joinedload(CourierProfile.user)).order_by(CourierProfile.id).all()


@router.post("", response_model=CourierOut, status_code=201)
def create_courier(
    _admin: AdminUser,
    payload: CourierCreate,
    db: Session = Depends(get_db),
) -> CourierProfile:
    if db.query(User).filter(User.email == str(payload.email).lower()).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.courier,
    )
    db.add(user)
    db.flush()
    cp = CourierProfile(user_id=user.id, vehicle_info=payload.vehicle_info)
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return db.query(CourierProfile).options(joinedload(CourierProfile.user)).filter(CourierProfile.id == cp.id).first()


@router.put("/{courier_id}", response_model=CourierOut)
def update_courier(
    courier_id: int,
    _admin: AdminUser,
    payload: CourierUpdate,
    db: Session = Depends(get_db),
) -> CourierProfile:
    cp = db.query(CourierProfile).filter(CourierProfile.id == courier_id).first()
    if cp is None:
        raise HTTPException(status_code=404, detail="Courier not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(cp, k, v)
    db.commit()
    return db.query(CourierProfile).options(joinedload(CourierProfile.user)).filter(CourierProfile.id == courier_id).first()


@router.delete("/{courier_id}", status_code=204)
def delete_courier(
    courier_id: int,
    _admin: AdminUser,
    db: Session = Depends(get_db),
) -> None:
    cp = db.query(CourierProfile).filter(CourierProfile.id == courier_id).first()
    if cp is None:
        raise HTTPException(status_code=404, detail="Courier not found")
    user = cp.user
    db.delete(cp)
    db.flush()
    db.delete(user)
    db.commit()
