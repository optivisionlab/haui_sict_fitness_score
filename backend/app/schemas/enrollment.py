from datetime import datetime
from typing import Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.models.enrollment import EnrollmentStatus
from app.schemas.common import BaseSchema


class StudentGradesSchema(BaseSchema):
    attendance_score: Optional[float] = None
    process_score: Optional[float] = None
    exam_score: Optional[float] = None
    final_score: Optional[float] = None
    letter_grade: Optional[str] = None
    is_passed: Optional[bool] = None


class EnrollmentBase(BaseSchema):
    user_id: str
    course_id: str
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    progress_percent: float = 0.0

    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_gender: Optional[str] = None

    course_name: Optional[str] = None
    teacher_name: Optional[str] = None
    exam_date: Optional[datetime] = None


class EnrollmentCreate(BaseSchema):
    user_id: str
    course_id: str
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_gender: Optional[str] = None
    course_name: Optional[str] = None
    teacher_name: Optional[str] = None
    exam_date: Optional[datetime] = None


class EnrollmentUpdate(BaseSchema):
    status: Optional[EnrollmentStatus] = None
    progress_percent: Optional[float] = None
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_gender: Optional[str] = None
    course_name: Optional[str] = None
    teacher_name: Optional[str] = None
    exam_date: Optional[datetime] = None
    completed_task_ids: Optional[list[str]] = None
    task_scores: Optional[dict[str, float]] = None
    grades: Optional[StudentGradesSchema] = None
    is_grade_locked: Optional[bool] = None
    note: Optional[str] = None


class EnrollmentRead(BaseSchema):
    id: PyObjectId
    user_id: str
    course_id: str
    status: EnrollmentStatus
    progress_percent: float

    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_gender: Optional[str] = None

    course_name: Optional[str] = None
    teacher_name: Optional[str] = None
    exam_date: Optional[datetime] = None
    completed_task_ids: list[str] = Field(default_factory=list)
    task_scores: dict[str, float] = Field(default_factory=dict)
    grades: StudentGradesSchema = Field(default_factory=StudentGradesSchema)
    is_grade_locked: bool = False
    note: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
