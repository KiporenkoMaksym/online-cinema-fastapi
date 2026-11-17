import re

from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain an uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain a lowercase letter")

        if not re.search(r"\d", password):
            raise ValueError("Password must contain a digit")

        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValueError("Password must contain a special character")

        return password


class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}


class ResendActivationSchema(BaseModel):
    email: EmailStr
