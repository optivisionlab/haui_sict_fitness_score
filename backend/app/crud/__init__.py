from .base import CRUDBase, to_object_id
from .camera import CRUDCamera, crud_camera
from .course import CRUDCourse, crud_course
from .enrollment import CRUDEnrollment, crud_enrollment
from .live_result import CRUDLiveResult, crud_live_result
from .sport import CRUDSport, crud_sport
from .task import CRUDTask, crud_task
from .user import CRUDUser, crud_user
from .video_result import CRUDVideoResult, crud_video_result

__all__ = [
    # Base
    "CRUDBase",
    "to_object_id",
    # User
    "CRUDUser",
    "crud_user",
    # Course
    "CRUDCourse",
    "crud_course",
    # Enrollment
    "CRUDEnrollment",
    "crud_enrollment",
    # Sport
    "CRUDSport",
    "crud_sport",
    # Task
    "CRUDTask",
    "crud_task",
    # Camera
    "CRUDCamera",
    "crud_camera",
    # Video Result
    "CRUDVideoResult",
    "crud_video_result",
    # Live Result
    "CRUDLiveResult",
    "crud_live_result",
]
