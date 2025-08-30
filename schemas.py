from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field
from pydantic import field_validator
from pydantic.config import ConfigDict


PASSWORD_REGEX = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+=-]{8,}$")


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    plan: str | None = Field(default=None)
    addons: List[str] | None = Field(default=None)
    notification_prefs: Dict[str, Any] | None = Field(default=None)


class UserCreate(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)

    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError("Password must be at least 8 characters with at least 1 letter and 1 number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8)
    plan: Optional[str] = None
    addons: Optional[List[str]] = None
    notification_prefs: Optional[Dict[str, Any]] = None

    @field_validator("password")
    def validate_password_strength_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not PASSWORD_REGEX.match(v):
            raise ValueError("Password must be at least 8 characters with at least 1 letter and 1 number")
        return v


class UserOut(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    plan: str
    addons: List[str]
    notification_prefs: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PaginatedUsers(BaseModel):
    total: int
    items: List[UserOut]


class Invoice(BaseModel):
    id: str
    date: str
    amount: float
    status: str
    pdf_url: str


