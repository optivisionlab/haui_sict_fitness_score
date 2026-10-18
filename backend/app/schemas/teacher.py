from datetime import datetime
from typing import Any, Optional
from pydantic import Field

from app.models.base import PyObjectId
from app.models.course import CourseStatus
from app.models.enrollment import EnrollmentStatus
from app.models.task import TaskCategory
from app.schemas.common import BaseSchema
from app.schemas.course import GradingFormulaSchema
from app.schemas.enrollment import StudentGradesSchema


class TeacherCourseItem(BaseSchema):
    id: PyObjectId
    code: Optional[str] = None
    name: str
    student_total: int = 0
    status: CourseStatus = CourseStatus.IN_PROGRESS
    is_grade_locked: bool = False
    allow_practice_submission: bool = True
    allow_exam_submission: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None


class TeacherCourseDetail(TeacherCourseItem):
    desc: Optional[str] = None
    teacher_id: str
    teacher_name: str
    grade_locked_at: Optional[datetime] = None
    grading_formula: GradingFormulaSchema = Field(default_factory=GradingFormulaSchema)
    total_weeks: int = 0
    total_tasks: int = 0


class SubmissionLockResponse(BaseSchema):
    course_id: str
    allow_practice_submission: bool
    allow_exam_submission: bool
    updated_at: datetime


class GradebookTaskItem(BaseSchema):
    id: str
    title: str
    category: TaskCategory


class GradebookStudentItem(BaseSchema):
    enrollment_id: str
    user_id: str
    student_code: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    gender: Optional[str] = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    progress_percent: float = 0.0
    task_scores: dict[str, float] = Field(default_factory=dict)
    grades: StudentGradesSchema = Field(default_factory=StudentGradesSchema)
    note: Optional[str] = None


class GradebookResponse(BaseSchema):
    course_id: str
    is_grade_locked: bool
    formula: GradingFormulaSchema
    task_list: list[GradebookTaskItem] = Field(default_factory=list)
    students: list[GradebookStudentItem] = Field(default_factory=list)


class SingleGradeUpdate(BaseSchema):
    enrollment_id: str
    attendance_score: Optional[float] = None
    exam_score: Optional[float] = None
    note: Optional[str] = None


class BatchGradeUpdateRequest(BaseSchema):
    updates: list[SingleGradeUpdate] = Field(default_factory=list)


class BatchGradeUpdateResponse(BaseSchema):
    updated_count: int


class FinalizeGradesRequest(BaseSchema):
    confirm: bool = True
    final_remarks: Optional[str] = None
    force: bool = False  # Nếu True, tự động gán điểm 0 cho sinh viên thiếu điểm thi


class FinalizeGradesResponse(BaseSchema):
    course_id: str
    is_grade_locked: bool
    grade_locked_at: datetime
    locked_by: str
    total_students_graded: int
    passed_count: int
    failed_count: int


class UnlockGradesRequest(BaseSchema):
    reason: str


class UnlockGradesResponse(BaseSchema):
    course_id: str
    is_grade_locked: bool
    unlocked_at: datetime


class GradeDistribution(BaseSchema):
    a: int = 0
    b: int = 0
    c: int = 0
    d: int = 0
    f: int = 0


class CourseStatsResponse(BaseSchema):
    course_id: str
    total_students: int
    pass_count: int
    fail_count: int
    pass_rate_percent: float
    average_score: float
    highest_score: float
    lowest_score: float
    grade_distribution: GradeDistribution = Field(default_factory=GradeDistribution)
    submission_rate: float
