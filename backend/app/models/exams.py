from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.classes import Class
    from app.models.result import Result


class ClassExam(SQLModel, table=True):
    __tablename__ = "class_exam"
    class_id: int = Field(sa_column=Column(ForeignKey("classes.class_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True))
    exam_id: int = Field(sa_column=Column(ForeignKey("exams.exam_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True))
    exam_date: Optional[datetime] = None
    status: Optional[str] = Field(default="active", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExamBase(SQLModel):
    # class_id removed: relation is now many-to-many via class_exam
    title: str = Field(max_length=255)
    description: Optional[str] = None

class Exam(ExamBase, table=True):
    __tablename__ = "exams"

    exam_id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    # Many-to-many relationship to classes via ClassExam
    classes: List["Class"] = Relationship(back_populates="exams", link_model=ClassExam)
    results: List["Result"] = Relationship(back_populates="exam")