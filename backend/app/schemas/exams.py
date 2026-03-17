from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ExamRead(BaseModel):
    exam_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
