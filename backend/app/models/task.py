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


class RecordingMode(str, Enum):
    """Cách quay video của bài (quyết định mô hình AI chấm)."""
    DIRECT = "direct"   # Quay trực diện, gần người đánh: VideoMAE + BEATs
    MATCH = "match"     # Quay đối kháng, xa, thấy cả sân: YOLO26s + trọng tài theo đường bay


class TargetZone(str, Enum):
    """Vùng đích của bài đối kháng (công thức 26), trên nửa sân đối phương."""
    FULL = "full"                    # Cả nửa sân
    KITCHEN = "kitchen"              # Vùng cấm vô lê (bài Dink)
    DEEP = "deep"                    # Sau vùng cấm vô lê
    SERVICE_LEFT = "service_left"    # Ô giao bóng bên trái (nhìn từ camera)
    SERVICE_RIGHT = "service_right"  # Ô giao bóng bên phải (nhìn từ camera)


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
    # None với dữ liệu cũ = quay trực diện
    recording_mode: Optional[RecordingMode] = None
    target_zone: Optional[TargetZone] = None  # Chỉ dùng khi recording_mode = "match"
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


def task_recording_mode(task) -> RecordingMode:
    mode = getattr(task, "recording_mode", None)
    return RecordingMode(mode) if mode else RecordingMode.DIRECT


def grading_mode(task, sport_mode: str) -> str:
    """Mode gửi AI: MATCH cho bài quay đối kháng, ngược lại mode của môn (VIDEO / CAMERA)."""
    if str(sport_mode).upper() == "VIDEO" and task_recording_mode(task) == RecordingMode.MATCH:
        return "MATCH"
    return str(sport_mode).upper()
