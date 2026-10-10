from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from pydantic import Field

from .base import BaseDocument


class VideoResult(BaseDocument):
    __collection__: ClassVar[str] = "video_results"

    task_id: str
    sport_id: str
    user_id: str

    # Denormalized fields (Tối ưu query hiển thị danh sách bài chấm)
    course_id: Optional[str] = None
    student_name: Optional[str] = None
    student_code: Optional[str] = None
    task_title: Optional[str] = None

    attempt_no: int = 1
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    pending: bool = True
    video_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    duration_sec: Optional[int] = None

    metrics: dict[str, Any] = Field(default_factory=dict)  # Schemaless theo từng môn
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None

    # GV chấm tay (override điểm AI)
    final_score: Optional[float] = None
    teacher_comment: Optional[str] = None
    graded_by: Optional[str] = None
    graded_at: Optional[datetime] = None
