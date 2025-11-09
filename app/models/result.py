from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class ResultBase(SQLModel):
    user_id: int = Field(foreign_key="users.user_id")
    exam_id: int = Field(foreign_key="exams.exam_id")
    step: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class Result(ResultBase, table=True):
    __tablename__ = "results"
    
    result_id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: "User" = Relationship(back_populates="results")
    exam: "Exam" = Relationship(back_populates="results")
