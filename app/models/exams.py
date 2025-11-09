from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ExamBase(SQLModel):
    class_id: int = Field(foreign_key="classes.class_id")
    title: str = Field(max_length=255)
    description: Optional[str] = None
    exam_date: Optional[datetime] = None
    max_score: float = Field(default=10.00)


class Exam(ExamBase, table=True):
    __tablename__ = "exams"
    
    exam_id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    class_: "Class" = Relationship(back_populates="exams")
    results: List["Result"] = Relationship(back_populates="exam")