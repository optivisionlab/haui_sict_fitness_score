from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional

from .base import BaseDocument


class TaskCategory(str, Enum):
    PRACTICE = "practice"
    EXAM = "exam"


class GradingMethod(str, Enum):
    HIGHEST = "highest"
    LATEST = "latest"
    AVERAGE = "average"


class Task(BaseDocument):
    __collection__: ClassVar[str] = "tasks"

    course_id: str
    sport_id: str

    title: str
    category: TaskCategory = TaskCategory.PRACTICE
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None  # Giây
    max_attempts: Optional[int] = None  # None = không giới hạn
    is_locked: bool = False

    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None

    camera_id: Optional[str] = None  # Khi mode = "camera"

