from datetime import datetime
from typing import Any, Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.schemas.common import BaseSchema


class VideoResultCreate(BaseSchema):
    task_id: str
    sport_id: str
    user_id: Optional[str] = None
    attempt_no: Optional[int] = 1
    video_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    duration_sec: Optional[int] = None


class VideoResultAIUpdate(BaseSchema):
    pending: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None


class VideoResultTeacherGrade(BaseSchema):
    final_score: float = Field(..., ge=0.0, le=10.0, description="Điểm chấm của giáo viên (thang điểm 10)")
    teacher_comment: Optional[str] = None
    graded_by: Optional[str] = None


class VideoResultRead(BaseSchema):
    id: PyObjectId
    task_id: str
    sport_id: str
    user_id: str
    attempt_no: int = 1
    submitted_at: Optional[datetime] = None
    pending: bool = True
    video_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    duration_sec: Optional[int] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None
    final_score: Optional[float] = None
    teacher_comment: Optional[str] = None
    graded_by: Optional[str] = None
    graded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PresignedUrlResponse(BaseSchema):
    video_url: str
    expires_in_seconds: int = 7200


class VideoResultStatusResponse(BaseSchema):
    id: str
    pending: bool
    ai_score: Optional[float] = None
    final_score: Optional[float] = None


class SubmissionItemResponse(BaseSchema):
    id: str
    user_id: str
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    attempt_no: int = 1
    submitted_at: Optional[datetime] = None
    pending: bool = True
    video_url: Optional[str] = None
    duration_sec: Optional[int] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None
    final_score: Optional[float] = None
    teacher_comment: Optional[str] = None
    graded_by: Optional[str] = None
    graded_at: Optional[datetime] = None
