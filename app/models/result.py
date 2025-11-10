from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, Integer, Numeric


class ResultBase(SQLModel):
    user_id: int = Field(
        sa_column=Column(ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    )
    exam_id: int = Field(
        sa_column=Column(ForeignKey("exams.exam_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    )
    # step is non-nullable in DB and must be provided/assigned by service; default to 1
    step: int = Field(default=1, sa_column=Column(Integer, nullable=False))
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

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401
    from app.models.exams import Exam  # noqa: F401
