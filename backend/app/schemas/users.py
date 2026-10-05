from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    user_name: str
    full_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    password: str
    user_role: UserRole = UserRole.student
    date_of_birth: Optional[date] = None


class UserRead(BaseModel):
    user_id: int
    user_name: str
    full_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    user_role: UserRole
    user_status: UserStatus
    date_of_birth: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

        
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    user_status: Optional[UserStatus] = "active"
    date_of_birth: Optional[date] = None


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

    
class TokenData(BaseModel):
    user_id: int
    user_role: str