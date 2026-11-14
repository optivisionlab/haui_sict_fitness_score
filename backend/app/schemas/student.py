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

    tasks: list[StudentTaskGradeItem] = Field(default_factory=list)
