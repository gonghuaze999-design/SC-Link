from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    display_name: str
    role: str
    status: str
    phone: str
    email: str
    last_login_at: datetime | None
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    user: UserOut


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str = Field(default="", max_length=64)
    role: str = "user"
    password: str = Field(min_length=8, max_length=64)
    phone: str = Field(default="", max_length=32)
    email: str = Field(default="", max_length=128)


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    status: str | None = None
    phone: str | None = None
    email: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=64)


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    action: str
    entity_type: str
    entity_id: str
    detail: str
    old_value: dict | None
    new_value: dict | None
    ip: str
    created_at: datetime


class LoginLogOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    result: str
    detail: str
    ip: str
    created_at: datetime
