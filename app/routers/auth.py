from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == str(payload.email)).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=str(payload.email).lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    """OAuth2 form: username = email, password = password."""
    email = (form_data.username or "").strip().lower()
    user = db.query(User).filter(User.email == email).first()
    from app.security import verify_password

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")
    token = create_access_token(user.email, user.role)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
