from pydantic import EmailStr, ConfigDict, Field, field_validator, BaseModel as Base
import re
from src.schemas import BaseModel


class UserBase(BaseModel):
    username: str
    email: EmailStr = Field(description="Email is required.")


class User(UserBase):
    id: int


class UserCreate(UserBase):
    password: str = Field(
        min_length=8, max_length=30, description="Must be between 8 and 30 characters."
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"\d", value):
            raise ValueError("Must contain at least one digit.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Must contain at least one lowercase character.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Must contain at least one uppercase character.")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(Base):
    access_token: str
    token_type: str
