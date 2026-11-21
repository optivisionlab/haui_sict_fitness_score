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
    """Điểm tổng kết = Chuyên cần × attendance + Quá trình × practice + Thi × exam."""
    attendance_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    practice_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    exam_weight: float = Field(default=0.6, ge=0.0, le=1.0)


class ExamEligibility(EmbeddedModel):
    """Điều kiện được dự thi kết thúc học phần (GV cấu hình theo lớp)."""
    enabled: bool = True
    min_attendance_score: float = Field(default=5.0, ge=0.0, le=10.0)
    min_process_score: float = Field(default=4.0, ge=0.0, le=10.0)


class LessonItemType(str, Enum):
    LESSON = "lesson"
    PRACTICE = "practice"


class LessonItem(EmbeddedModel):
    title: str
    type: LessonItemType
    task_id: Optional[str] = None


class ClassSession(EmbeddedModel):
    """Một buổi học cố định trong tuần của lớp học phần."""
    day_of_week: int = Field(ge=2, le=8)    # 2 = Thứ Hai ... 7 = Thứ Bảy, 8 = Chủ nhật
    periods: str                            # VD: "1-3" (tiết 1 đến 3)
    location: Optional[str] = None          # VD: "Sân Pickleball - Cơ sở 1"


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

    # Bộ môn thể chất (Master Enum)
    sport_id: Optional[str] = None
    sport_name: Optional[str] = None
    sport_code: Optional[str] = None        # VD: PhysicalSubjectCode.PICKLEBALL ("PICKLEBALL")

    # Học kỳ & năm học (Quy chuẩn: YYYY-YYYY.T)
    semester: Optional[str] = None          # VD: "2026-2027.1"
    semester_name: Optional[str] = None     # VD: "Học kỳ 1 (2026 - 2027)"
    academic_year: Optional[str] = None     # VD: "2026-2027"
    term: Optional[int] = None              # VD: 1, 2, 3

    status: CourseStatus = CourseStatus.IN_PROGRESS
    is_grade_locked: bool = False
    grade_locked_at: Optional[datetime] = None
    grade_locked_by: Optional[str] = None

    allow_practice_submission: bool = True
    allow_exam_submission: bool = True

    grading_formula: GradingFormula = Field(default_factory=GradingFormula)
    exam_eligibility: ExamEligibility = Field(default_factory=ExamEligibility)

    student_total: int = 0
    schedule: list[ClassSession] = []
    weeks: list[Week] = []

