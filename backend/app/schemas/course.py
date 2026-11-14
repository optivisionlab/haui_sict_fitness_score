from datetime import datetime
from typing import Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.models.course import CourseStatus, LessonItemType
from app.schemas.common import BaseSchema


class GradingFormulaSchema(BaseSchema):
    attendance_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    practice_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    exam_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class LessonItemBase(BaseSchema):
    title: str
    type: LessonItemType = LessonItemType.LESSON
    task_id: Optional[str] = None


class LessonItemCreate(LessonItemBase):
    pass


class LessonItemRead(LessonItemBase):
    pass


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

    status: CourseStatus = CourseStatus.IN_PROGRESS
    is_grade_locked: bool = False
    grade_locked_at: Optional[datetime] = None
    grade_locked_by: Optional[str] = None
    allow_practice_submission: bool = True
    allow_exam_submission: bool = True
    grading_formula: GradingFormulaSchema = Field(default_factory=GradingFormulaSchema)

    weeks: list[WeekRead] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubmissionLockUpdate(BaseSchema):
    allow_practice_submission: Optional[bool] = None
    allow_exam_submission: Optional[bool] = None
