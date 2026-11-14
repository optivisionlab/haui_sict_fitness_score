from .camera import CameraCreate, CameraRead, CameraUpdate
from .common import (
    ApiResponse,
    BaseSchema,
    MessageResponse,
    PaginatedResponse,
    PyObjectId,
    error_response,
    success_response,
)
from .course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    GradingFormulaSchema,
    LessonItemCreate,
    LessonItemRead,
    SubmissionLockUpdate,
    WeekCreate,
    WeekRead,
    WeekUpdate,
)
from .enrollment import (
    EnrollmentCreate,
    EnrollmentRead,
    EnrollmentUpdate,
    StudentGradesSchema,
)
from .live_result import LiveResultCreate, LiveResultRead, LiveResultUpdate
from .notification import NotificationCreate, NotificationRead
from .sport import ScoringConfigSchema, SportCreate, SportRead, SportUpdate
from .student import StudentGradeViewResponse, StudentTaskGradeItem
from .task import TaskCreate, TaskLockUpdate, TaskRead, TaskUpdate
from .teacher import (
    BatchGradeUpdateRequest,
    BatchGradeUpdateResponse,
    CourseStatsResponse,
    FinalizeGradesRequest,
    FinalizeGradesResponse,
    GradebookResponse,
    GradebookStudentItem,
    GradebookTaskItem,
    SingleGradeUpdate,
    SubmissionLockResponse,
    TeacherCourseDetail,
    TeacherCourseItem,
    UnlockGradesRequest,
    UnlockGradesResponse,
)
from .user import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)
from .video_result import (
    SubmissionItemResponse,
    VideoResultAIUpdate,
    VideoResultCreate,
    VideoResultRead,
    VideoResultStatusResponse,
    VideoResultTeacherGrade,
)

__all__ = [
    # Common
    "BaseSchema",
    "PyObjectId",
    "MessageResponse",
    "PaginatedResponse",
    "ApiResponse",
    "success_response",
    "error_response",
    # User
    "UserCreate",
    "UserUpdate",
    "UserRead",
    "UserLogin",
    "Token",
    "TokenData",
    # Camera
    "CameraCreate",
    "CameraUpdate",
    "CameraRead",
    # Course
    "LessonItemCreate",
    "LessonItemRead",
    "WeekCreate",
    "WeekUpdate",
    "WeekRead",
    "CourseCreate",
    "CourseUpdate",
    "CourseRead",
    "GradingFormulaSchema",
    "SubmissionLockUpdate",
    # Enrollment
    "EnrollmentCreate",
    "EnrollmentUpdate",
    "EnrollmentRead",
    "StudentGradesSchema",
    # Sport
    "ScoringConfigSchema",
    "SportCreate",
    "SportUpdate",
    "SportRead",
    # Task
    "TaskCreate",
    "TaskUpdate",
    "TaskRead",
    "TaskLockUpdate",
    # Video Result
    "VideoResultCreate",
    "VideoResultAIUpdate",
    "VideoResultTeacherGrade",
    "VideoResultRead",
    "VideoResultStatusResponse",
    "SubmissionItemResponse",
    # Live Result
    "LiveResultCreate",
    "LiveResultUpdate",
    "LiveResultRead",
    # Teacher
    "TeacherCourseItem",
    "TeacherCourseDetail",
    "SubmissionLockResponse",
    "GradebookTaskItem",
    "GradebookStudentItem",
    "GradebookResponse",
    "SingleGradeUpdate",
    "BatchGradeUpdateRequest",
    "BatchGradeUpdateResponse",
    "FinalizeGradesRequest",
    "FinalizeGradesResponse",
    "UnlockGradesRequest",
    "UnlockGradesResponse",
    "CourseStatsResponse",
    # Student
    "StudentTaskGradeItem",
    "StudentGradeViewResponse",
    # Notification
    "NotificationCreate",
    "NotificationRead",
]
