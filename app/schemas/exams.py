from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExamCreate(BaseModel):
    class_id: int
    title: str
    description: Optional[str] = None
    exam_date: Optional[datetime] = None
    max_score: float = 10.00


class ExamRead(BaseModel):
    exam_id: int
    class_id: int
    title: str
    description: Optional[str] = None
    exam_date: Optional[datetime] = None
    max_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    exam_date: Optional[datetime] = None
    max_score: Optional[float] = None


class ResultCreate(BaseModel):
    user_id: int
    exam_id: int
    step: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ResultRead(BaseModel):
    result_id: int
    user_id: int
    exam_id: int
    step: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResultUpdate(BaseModel):
    step: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None