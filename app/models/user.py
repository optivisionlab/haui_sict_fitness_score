from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
from enum import Enum

if TYPE_CHECKING:
    from app.models.classes import Class
    from app.models.result import Result


class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"


class UserClass(SQLModel, table=True):
    __tablename__ = "user_class"
    
    user_id: int = Field(
        sa_column=Column(ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    )
    class_id: int = Field(
        sa_column=Column(ForeignKey("classes.class_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    )


class UserBase(SQLModel):
    user_name: str = Field(max_length=150, index=True, unique=True)
    full_name: Optional[str] = Field(max_length=255, default=None)
    email: str = Field(max_length=255, index=True, unique=True)
    phone_number: Optional[str] = Field(max_length=50, default=None)
    user_code: Optional[str] = Field(max_length=100, default=None, unique=True)
    user_role: UserRole = Field(default=UserRole.student)
    user_status: UserStatus = Field(default=UserStatus.active)
    date_of_birth: Optional[date] = None


class User(UserBase, table=True):
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    teaching_classes: List["Class"] = Relationship(
        back_populates="teacher",
        sa_relationship_kwargs={"foreign_keys": "[Class.teacher_id]"}
    )
    enrolled_classes: List["Class"] = Relationship(
        back_populates="students",
        link_model=UserClass
    )
    results: List["Result"] = Relationship(back_populates="user")
