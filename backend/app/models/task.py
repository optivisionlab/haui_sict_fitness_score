from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional

from .base import BaseDocument


class TaskCategory(str, Enum):
    PRACTICE = "practice"
    EXAM = "exam"


class TaskKind(str, Enum):
    """Vị trí của bài trong cấu trúc điểm học phần."""
    REGULAR = "regular"   # Kiểm tra thường xuyên (TX) -> điểm quá trình, có phần luyện tập
    MIDTERM = "midterm"   # Thi giữa kỳ -> tính vào điểm quá trình
    FINAL = "final"       # Thi kết thúc học phần -> điểm thi


class GradingMethod(str, Enum):
    HIGHEST = "highest"
    LATEST = "latest"
    AVERAGE = "average"


class Task(BaseDocument):
    __collection__: ClassVar[str] = "tasks"

    course_id: str
    sport_id: str

    title: str
    description: Optional[str] = None  # Yêu cầu kỹ thuật hiển thị cho sinh viên
    category: TaskCategory = TaskCategory.PRACTICE
    kind: Optional[TaskKind] = None  # None với dữ liệu cũ: suy ra bằng task_kind()
    grading_method: GradingMethod = GradingMethod.HIGHEST
    time_limit: Optional[int] = None  # Giây
    max_attempts: Optional[int] = None  # None = không giới hạn
    is_locked: bool = False

    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None

    camera_id: Optional[str] = None  # Khi mode = "camera"
    instruction_video_url: Optional[str] = None  # Đường dẫn MinIO hoặc URL video hướng dẫn soạn bài



def task_kind(task) -> TaskKind:
    """Loại bài; dữ liệu cũ chưa có `kind` thì suy ra từ category và tiêu đề."""
    kind = getattr(task, "kind", None)
    if kind:
        return TaskKind(kind)
    if getattr(task, "category", TaskCategory.PRACTICE) != TaskCategory.EXAM:
        return TaskKind.REGULAR
    title = (getattr(task, "title", "") or "").lower()
    return TaskKind.MIDTERM if ("giữa" in title or "midterm" in title) else TaskKind.FINAL


def category_for_kind(kind: TaskKind) -> TaskCategory:
    return TaskCategory.PRACTICE if kind == TaskKind.REGULAR else TaskCategory.EXAM
