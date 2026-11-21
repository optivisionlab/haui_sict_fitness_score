from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import Field, model_validator

SubmissionMode = Literal["practice", "test"]

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


class VideoUploadUrlRequest(BaseSchema):
    task_id: str
    course_id: Optional[str] = None
    file_name: str
    content_type: str
    file_size: int = Field(..., gt=0)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    mode: SubmissionMode = "test"


class VideoUploadUrlResponse(BaseSchema):
    upload_id: str
    result_id: str
    object_key: str
    upload_url: str
    expires_in: int


class VideoUploadConfirmRequest(BaseSchema):
    upload_id: str


class VideoResultAIUpdate(BaseSchema):
    pending: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None
    annotated_object_key: Optional[str] = None


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
    mode: str = "test"
    has_annotated_video: bool = False
    submitted_at: Optional[datetime] = None
    pending: bool = True
    status: str = "pending"
    error: Optional[str] = None
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


    @model_validator(mode="before")
    @classmethod
    def _flag_annotated_video(cls, data: Any) -> Any:
        """Chỉ báo có video AI hay không; không lộ object key của MinIO ra ngoài."""
        if isinstance(data, dict):
            key = data.get("annotated_object_key") or data.get("annotatedObjectKey")
            return {**data, "has_annotated_video": True} if key else data
        if getattr(data, "annotated_object_key", None):
            return {**data.model_dump(), "has_annotated_video": True}
        return data


class PresignedUrlResponse(BaseSchema):
    video_url: str
    expires_in_seconds: int = 7200


class VideoResultStatusResponse(BaseSchema):
    id: str
    mode: str = "test"
    pending: bool
    status: str = "pending"
    error: Optional[str] = None
    ai_score: Optional[float] = None
    final_score: Optional[float] = None


class SubmissionItemResponse(BaseSchema):
    id: str
    user_id: str
    status: str = "pending"
    error: Optional[str] = None
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
