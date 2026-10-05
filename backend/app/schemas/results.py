from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResultCreate(BaseModel):
    user_id: int
    exam_id: int
    step: Optional[int] = None
    lap: Optional[int] = 1
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ResultRead(BaseModel):
    result_id: int
    user_id: int
    exam_id: int
    step: Optional[int] = None
    lap: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResultUpdate(BaseModel):
    step: Optional[int] = None
    lap: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None