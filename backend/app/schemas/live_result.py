from datetime import datetime
from typing import Any, Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.schemas.common import BaseSchema


class LiveResultCreate(BaseSchema):
    task_id: str
    sport_id: str
    user_id: str
    camera_id: str


class LiveResultUpdate(BaseSchema):
    completed_at: Optional[datetime] = None
    metrics: Optional[dict[str, Any]] = None
    score: Optional[float] = Field(default=None, ge=0.0, le=10.0)


class LiveResultFinishRequest(BaseSchema):
    score: Optional[float] = Field(default=None, ge=0.0, le=10.0, description="Điểm số đạt được (0.0 - 10.0)")
    metrics: Optional[dict[str, Any]] = Field(default=None, description="Chỉ số phân tích kỹ thuật")


class LiveResultRead(BaseSchema):
    id: PyObjectId
    task_id: str
    sport_id: str
    user_id: str
    camera_id: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
