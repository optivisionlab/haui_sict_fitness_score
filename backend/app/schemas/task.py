from datetime import datetime
from typing import Optional

from app.models.base import PyObjectId
from app.models.task import GradingMethod, TaskCategory, TaskKind
from pydantic import Field

from app.schemas.common import BaseSchema


class TaskBase(BaseSchema):
    course_id: str
    sport_id: str
    title: str
    description: Optional[str] = None
    category: TaskCategory = TaskCategory.PRACTICE
    kind: Optional[TaskKind] = None
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: bool = False
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None
    instruction_video_url: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseSchema):
    course_id: Optional[str] = None
    sport_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TaskCategory] = None
    kind: Optional[TaskKind] = None
    grading_method: Optional[GradingMethod] = None
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: Optional[bool] = None
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None
    instruction_video_url: Optional[str] = None


class TaskLockUpdate(BaseSchema):
    is_locked: bool


class TaskRead(BaseSchema):
    id: PyObjectId
    course_id: str
    sport_id: str
    sport_name: Optional[str] = None
    sport_mode: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: TaskCategory = TaskCategory.PRACTICE
    kind: Optional[TaskKind] = None
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None
    max_attempts: Optional[int] = None
    is_locked: bool = False
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    camera_id: Optional[str] = None
    instruction_video_url: Optional[str] = None
    submitted_count: Optional[int] = None
    graded_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TeacherTaskUpsert(BaseSchema):
    """Giảng viên tạo / sửa bài kiểm tra của lớp mình phụ trách."""
    title: str = Field(min_length=1, max_length=200)
    kind: TaskKind = TaskKind.REGULAR
    description: Optional[str] = Field(default=None, max_length=2000)
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = Field(default=None, ge=1, le=3600, description="Thời lượng video tối đa (giây)")
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    is_locked: bool = False
