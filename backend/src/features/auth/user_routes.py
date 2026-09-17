from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import AppError
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.auth.user_schema import UserCreate, UserLogin

router = APIRouter(prefix="/api/auth", tags=["Users"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = user_service.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = user_service.create_user(db, user_in)
    return user_service.get_access_token(user.email)


@router.post("/token", status_code=status.HTTP_200_OK)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = user_service.get_user_by_email(db, email=form_data.username)
    if not user or not user_service.check_password_hash(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password.",
        )

    return user_service.get_access_token(user.email)


@router.post("/login", status_code=status.HTTP_200_OK)
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    existing_user = user_service.get_user_by_email(db, email=user_in.email)
    if not existing_user or not user_service.check_password_hash(
        user_in.password, existing_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password or email.",
        )
    return user_service.get_access_token(existing_user.email)


@router.get("/me")
def check_auth():
    try:
        user: User = Depends(user_service.get_current_user)
    except AppError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message)
    return user
