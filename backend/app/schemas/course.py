from datetime import datetime
from typing import Optional
from pydantic import Field, model_validator

from app.models.base import PyObjectId
from app.models.course import CourseStatus, LessonItemType
from app.schemas.common import BaseSchema


class GradingFormulaSchema(BaseSchema):
    attendance_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    practice_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    exam_weight: float = Field(default=0.6, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _weights_sum_to_one(self):
        total = self.attendance_weight + self.practice_weight + self.exam_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Tổng tỷ trọng phải bằng 1 (hiện tại {round(total, 4)})")
        return self


class ExamEligibilitySchema(BaseSchema):
    enabled: bool = True
    min_attendance_score: float = Field(default=5.0, ge=0.0, le=10.0)
    min_process_score: float = Field(default=4.0, ge=0.0, le=10.0)


class CourseGradingSettings(BaseSchema):
    """GV cấu hình tỷ trọng điểm và điều kiện dự thi của lớp."""
    grading_formula: GradingFormulaSchema
    exam_eligibility: ExamEligibilitySchema


class LessonItemBase(BaseSchema):
    title: str
    type: LessonItemType = LessonItemType.LESSON
    task_id: Optional[str] = None


class LessonItemCreate(LessonItemBase):
    pass


class LessonItemRead(LessonItemBase):
    pass


class ClassSessionSchema(BaseSchema):
    day_of_week: int = Field(ge=2, le=8)
    periods: str = Field(min_length=1, max_length=20)
    location: Optional[str] = Field(default=None, max_length=200)


class WeekBase(BaseSchema):
    order: int
    title: str


class WeekCreate(WeekBase):
    items: list[LessonItemCreate] = Field(default_factory=list)


class WeekUpdate(BaseSchema):
    order: Optional[int] = None
    title: Optional[str] = None
    items: Optional[list[LessonItemCreate]] = None


class WeekRead(WeekBase):
    items: list[LessonItemRead] = Field(default_factory=list)


class CourseBase(BaseSchema):
    name: str
    teacher_id: str
    teacher_name: Optional[str] = None
    key: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None
    code: Optional[str] = None
    desc: Optional[str] = None

    sport_id: Optional[str] = None
    sport_name: Optional[str] = None
    sport_code: Optional[str] = None
    semester: Optional[str] = None
    semester_name: Optional[str] = None
    academic_year: Optional[str] = None
    term: Optional[int] = None
    schedule: list[ClassSessionSchema] = Field(default_factory=list)

    status: CourseStatus = CourseStatus.IN_PROGRESS
    allow_practice_submission: bool = True
    allow_exam_submission: bool = True
    grading_formula: GradingFormulaSchema = Field(default_factory=GradingFormulaSchema)


class CourseCreate(CourseBase):
    weeks: list[WeekCreate] = Field(default_factory=list)


class CourseUpdate(BaseSchema):
    name: Optional[str] = None
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    key: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None
    code: Optional[str] = None
    desc: Optional[str] = None
    student_total: Optional[int] = None

    sport_id: Optional[str] = None
    sport_name: Optional[str] = None
    sport_code: Optional[str] = None
    semester: Optional[str] = None
    semester_name: Optional[str] = None
    academic_year: Optional[str] = None
    term: Optional[int] = None
    schedule: Optional[list[ClassSessionSchema]] = None

    status: Optional[CourseStatus] = None
    is_grade_locked: Optional[bool] = None
    allow_practice_submission: Optional[bool] = None
    allow_exam_submission: Optional[bool] = None
    grading_formula: Optional[GradingFormulaSchema] = None

    weeks: Optional[list[WeekCreate]] = None


class CourseRead(BaseSchema):
    id: PyObjectId
    key: Optional[str] = None
    name: str
    teacher_id: str
    teacher_name: Optional[str] = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None
    code: Optional[str] = None
    desc: Optional[str] = None
    student_total: int = 0

    sport_id: Optional[str] = None
    sport_name: Optional[str] = None
    sport_code: Optional[str] = None
    semester: Optional[str] = None
    semester_name: Optional[str] = None
    academic_year: Optional[str] = None
    term: Optional[int] = None
    schedule: list[ClassSessionSchema] = Field(default_factory=list)

    status: CourseStatus = CourseStatus.IN_PROGRESS
    is_grade_locked: bool = False
    grade_locked_at: Optional[datetime] = None
    grade_locked_by: Optional[str] = None
    allow_practice_submission: bool = True
    allow_exam_submission: bool = True
    grading_formula: GradingFormulaSchema = Field(default_factory=GradingFormulaSchema)
    exam_eligibility: ExamEligibilitySchema = Field(default_factory=ExamEligibilitySchema)

    weeks: list[WeekRead] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubmissionLockUpdate(BaseSchema):
    allow_practice_submission: Optional[bool] = None
    allow_exam_submission: Optional[bool] = None
