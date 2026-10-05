from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.features.auth import user_service
from src.features.auth.user_model import User as UserModel
from src.features.auth.user_schema import Token, User, UserCreate, UserLogin
from src.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["Users"])


@limiter.limit("20/hour")
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate, request: Request, db: Session = Depends(get_db)
) -> Token:
    existing_user = user_service.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = user_service.create_user(db, user_in)
    return user_service.get_access_token(user.email)


@limiter.limit("20/hour")
@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = user_service.get_user_by_email(db, email=form_data.username)
    if not user or not user_service.check_password_hash(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    return user_service.get_access_token(user.email)


@limiter.limit("20/hour")
@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login_user(
    user_in: UserLogin, request: Request, db: Session = Depends(get_db)
) -> Token:
    existing_user = user_service.get_user_by_email(db, email=user_in.email)

    if not existing_user or not user_service.check_password_hash(
        user_in.password, existing_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    return user_service.get_access_token(existing_user.email)


@limiter.limit("20/hour")
@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
def check_auth(
    request: Request, user: UserModel = Depends(user_service.get_current_user)
) -> UserModel:
    return user
