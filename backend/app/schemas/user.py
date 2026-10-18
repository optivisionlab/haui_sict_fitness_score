from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field

from app.models.base import PyObjectId
from app.models.user import UserRole
from app.schemas.common import BaseSchema


class UserBase(BaseSchema):
    name: str
    email: EmailStr
    role: UserRole = UserRole.STUDENT
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    user_status: Optional[str] = "active"
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    hometown: Optional[str] = None
    personal_email: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Mật khẩu tối thiểu 6 ký tự")


class UserUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(default=None, min_length=6)
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    user_status: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    hometown: Optional[str] = None
    personal_email: Optional[str] = None


class UserRead(BaseSchema):
    id: PyObjectId
    name: str
    email: EmailStr
    role: UserRole
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    user_status: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    hometown: Optional[str] = None
    personal_email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserRead] = None


class TokenData(BaseSchema):
    user_id: Optional[str] = None
    role: Optional[str] = None
