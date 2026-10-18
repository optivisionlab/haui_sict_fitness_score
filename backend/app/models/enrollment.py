from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional
from pydantic import Field

from .base import BaseDocument, EmbeddedModel


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    DONE = "done"
    DROPPED = "dropped"


class StudentGrades(EmbeddedModel):
    attendance_score: Optional[float] = None  # Điểm chuyên cần (hệ 10)
    process_score: Optional[float] = None     # Điểm quá trình (tính từ các bài practice)
    exam_score: Optional[float] = None        # Điểm thi kết thúc học phần
    final_score: Optional[float] = None       # Điểm tổng kết hệ 10
    letter_grade: Optional[str] = None        # Điểm chữ: A, B+, B, C+, C, D+, D, F
    is_passed: Optional[bool] = None          # Trạng thái Đạt hay Trượt


class Enrollment(BaseDocument):
    __collection__: ClassVar[str] = "enrollments"

    user_id: str
    course_id: str

    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    progress_percent: float = 0.0

    # Denormalized fields (Tối ưu Gradebook load 1-query không cần $lookup)
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_gender: Optional[str] = None

    course_name: Optional[str] = None
    teacher_name: Optional[str] = None
    exam_date: Optional[datetime] = None

    completed_task_ids: list[str] = []
    task_scores: dict[str, float] = {}

    # Điểm thành phần và tổng kết
    grades: StudentGrades = Field(default_factory=StudentGrades)
    is_grade_locked: bool = False
    note: Optional[str] = None

