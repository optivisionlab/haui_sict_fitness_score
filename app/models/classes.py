from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
from enum import Enum

# Import UserClass to use as link_model
from app.models.user import UserClass
from app.models.exams import ClassExam

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exams import Exam


class CourseType(str, Enum):
    running = "running"
    swimming = "swimming"
    cycling = "cycling"


class ClassStatus(str, Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class ClassBase(SQLModel):
    class_name: str = Field(max_length=255)
    course_type: CourseType = Field(default=CourseType.running)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    class_status: ClassStatus = Field(default=ClassStatus.active)


class Class(ClassBase, table=True):
    __tablename__ = "classes"
    
    class_id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: Optional[int] = Field(
        default=None,
        sa_column=Column(ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    teacher: Optional["User"] = Relationship(
        back_populates="teaching_classes",
        sa_relationship_kwargs={"foreign_keys": "[Class.teacher_id]"}
    )
    students: List["User"] = Relationship(
        back_populates="enrolled_classes",
        link_model=UserClass
    )
    # Many-to-many relationship to exams via ClassExam
    exams: List["Exam"] = Relationship(back_populates="classes", link_model=ClassExam)