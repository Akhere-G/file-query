from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    ServiceUnavailableError,
)
from src.features.auth import user_service
from src.features.auth.user_model import User as UserModel
from src.features.auth.user_schema import Token, User, UserCreate, UserLogin
from src.limiter import limiter
from src.settings import settings

router = APIRouter(prefix="/api/auth", tags=["Users"])

INCORRECT_LOGIN = "Incorrect email or password."


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def register_user(
    user_in: UserCreate, request: Request, db: Session = Depends(get_db)
) -> Token:
    if user_service.get_user_by_email(db, email=user_in.email):
        raise ConflictError("A user with this email already exists.")

    user = user_service.create_user(db, user_in)
    return user_service.get_access_token(user.email)


@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
@limiter.limit("20/hour")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = user_service.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise InvalidCredentialsError(INCORRECT_LOGIN)

    return user_service.get_access_token(user.email)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
@limiter.limit("20/hour")
def login_user(
    user_in: UserLogin, request: Request, db: Session = Depends(get_db)
) -> Token:
    user = user_service.authenticate(db, user_in.email, user_in.password)
    if user is None:
        raise InvalidCredentialsError(INCORRECT_LOGIN)

    return user_service.get_access_token(user.email)


@router.post("/demo", response_model=Token, status_code=status.HTTP_200_OK)
@limiter.limit("30/hour")
def start_demo(request: Request, db: Session = Depends(get_db)) -> Token:
    demo_user = user_service.get_demo_user(db)
    if demo_user is None:
        raise ServiceUnavailableError("The demo is not available right now.")

    return user_service.get_demo_access_token(demo_user)


@router.get("/me", response_model=User, status_code=status.HTTP_200_OK)
@limiter.limit("120/hour")
def check_auth(
    request: Request, user: UserModel = Depends(user_service.get_current_user)
) -> UserModel:
    return user
