import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import InvalidCredentialsError

from .user_model import User
from .user_schema import Token, UserCreate

load_dotenv()

SECRET_KEY: str = os.getenv("SECRET_KEY", "")
ALGORITHM: str = os.getenv("ALGORITHM", "")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

if not ALGORITHM:
    raise ValueError("Env variables are not present: ALGORITHM")
if not SECRET_KEY:
    raise ValueError("Env variables are not present: SECRET KEY")

oauth_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        email: str | None = payload.get("sub")
        if email is None:
            raise InvalidCredentialsError()
    except InvalidTokenError:
        raise InvalidCredentialsError()

    user = get_user_by_email(db, email=email)

    if user is None:
        raise InvalidCredentialsError()
    return user


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def check_password_hash(password: str, hash: str) -> bool:
    return pwd_context.verify(password, hash)


def get_user(db: Session, user_id: int):
    query = select(User).where(User.id == user_id)
    return db.execute(query).scalar_one_or_none()


def get_user_by_email(db: Session, email: str):
    query = select(User).where(User.email == email)
    return db.execute(query).scalar_one_or_none()


def create_user(db: Session, user_in: UserCreate):
    try:
        hashed_password = get_password_hash(user_in.password)

        user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=hashed_password,
        )

        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def get_access_token(email: str):
    access_token = create_access_token(data={"sub": email})

    return Token(access_token=access_token, token_type="bearer")
