from enum import Enum
from typing import ClassVar, Optional

from pydantic import EmailStr

from .base import BaseDocument


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(BaseDocument):
    __collection__: ClassVar[str] = "users"

    name: str
    email: EmailStr
    role: UserRole = UserRole.STUDENT
    password: str
    phone_number: Optional[str] = None
    user_code: Optional[str] = None
    user_status: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    hometown: Optional[str] = None
    personal_email: Optional[str] = None
