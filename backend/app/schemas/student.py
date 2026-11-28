from datetime import datetime
from typing import Optional
from pydantic import Field

from app.models.task import TaskCategory
from app.schemas.common import BaseSchema


class StudentTaskGradeItem(BaseSchema):
    task_id: str
    task_title: str
    category: TaskCategory
    weight: Optional[float] = None
    score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    status: str = "not_submitted"  # "not_submitted" | "pending" | "graded"
    instruction_video_url: Optional[str] = None
    kind: Optional[str] = None                     # regular | midterm | final
    technical_requirements: Optional[str] = None
    teacher_override: bool = False                 # Điểm do GV nhập tay

    # Cấu hình bài do giảng viên đặt (để FE không phải tự điền giá trị mặc định)
    grading_method: Optional[str] = None   # "highest" | "latest" | "average"
    time_limit: Optional[int] = None       # Giây; None = không giới hạn
    max_attempts: Optional[int] = None     # None = không giới hạn
    is_locked: bool = False
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    # Cách quay: direct (trực diện) | match (đối kháng: SV đánh dấu sân khi nộp)
    recording_mode: str = "direct"
    target_zone: Optional[str] = None


class StudentGradeViewResponse(BaseSchema):
    course_name: str
    teacher_name: str
    is_grade_locked: bool = False
    progress_percent: float = 0.0

    attendance_score: Optional[float] = None
    process_score: Optional[float] = None
    exam_score: Optional[float] = None
    final_score: Optional[float] = None
    letter_grade: Optional[str] = None
    is_passed: Optional[bool] = None
    is_eligible: Optional[bool] = None
    min_attendance_score: Optional[float] = None
    min_process_score: Optional[float] = None

    tasks: list[StudentTaskGradeItem] = Field(default_factory=list)
