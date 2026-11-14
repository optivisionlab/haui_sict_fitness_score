from datetime import datetime
from typing import Optional

from app.models.base import PyObjectId
from app.models.task import GradingMethod, TaskCategory
from app.schemas.common import BaseSchema


class TaskBase(BaseSchema):
    course_id: str
    sport_id: str
    title: str
    category: TaskCategory = TaskCategory.PRACTICE
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: bool = False
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseSchema):
    course_id: Optional[str] = None
    sport_id: Optional[str] = None
    title: Optional[str] = None
    category: Optional[TaskCategory] = None
    grading_method: Optional[GradingMethod] = None
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: Optional[bool] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None


class TaskLockUpdate(BaseSchema):
    is_locked: bool


class TaskRead(BaseSchema):
    id: PyObjectId
    course_id: str
    sport_id: str
    sport_name: Optional[str] = None
    sport_mode: Optional[str] = None
    title: str
    category: TaskCategory = TaskCategory.PRACTICE
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: bool = False
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None
    submitted_count: Optional[int] = None
    graded_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
