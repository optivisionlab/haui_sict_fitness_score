from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional
from pydantic import Field

from .base import BaseDocument, EmbeddedModel


class CourseStatus(str, Enum):
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GradingFormula(EmbeddedModel):
    attendance_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    practice_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    exam_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class LessonItemType(str, Enum):
    LESSON = "lesson"
    PRACTICE = "practice"


class LessonItem(EmbeddedModel):
    title: str
    type: LessonItemType
    task_id: Optional[str] = None


class Week(EmbeddedModel):
    order: int
    title: str
    items: list[LessonItem] = []

class Course(BaseDocument):
    __collection__: ClassVar[str] = "courses"

    key: Optional[str] = None
    name: str
    teacher_id: str
    teacher_name: str = ""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None
    code: Optional[str] = None
    desc: Optional[str] = None

    status: CourseStatus = CourseStatus.IN_PROGRESS
    is_grade_locked: bool = False
    grade_locked_at: Optional[datetime] = None
    grade_locked_by: Optional[str] = None

    allow_practice_submission: bool = True
    allow_exam_submission: bool = True

    grading_formula: GradingFormula = Field(default_factory=GradingFormula)

    student_total: int = 0
    weeks: list[Week] = []

