from typing import Any, Optional

from app.core.config import settings

LANE_SMALL = "small"
LANE_LARGE = "large"


def job_duration_sec(job: dict[str, Any], fallback: Any = None) -> Optional[float]:
    """Thời lượng video (giây) của job; None nếu không biết hoặc không hợp lệ."""
    value = job.get("durationSec")
    if value is None:
        value = fallback
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    return duration if duration > 0 else None


def resolve_lane(duration_sec: Optional[float]) -> str:
    """Video dài hơn ngưỡng đi làn large; thiếu thời lượng thì mặc định small."""
    if duration_sec is not None and duration_sec > settings.AI_LANE_THRESHOLD_SEC:
        return LANE_LARGE
    return LANE_SMALL


def lane_topic(lane: str) -> str:
    if lane == LANE_LARGE:
        return settings.KAFKA_TOPIC_GRADING_JOBS_LARGE
    return settings.KAFKA_TOPIC_GRADING_JOBS_SMALL


def job_file_size_mb(job: dict[str, Any], fallback: Any = None) -> Optional[float]:
    value = job.get("fileSize")
    if value is None:
        value = fallback
    try:
        size = float(value)
    except (TypeError, ValueError):
        return None
    return size / (1024 * 1024) if size > 0 else None


def compute_ai_timeout(job: dict[str, Any]) -> float:
    """
    Timeout gọi AI = BASE + PER_VIDEO_SEC x durationSec + PER_MB x fileSize(MB), trần AI_TIMEOUT_MAX_SEC.
    AI phải tải video từ MinIO trước khi chấm, nên dung lượng chiếm phần lớn thời gian khi mạng chậm.
    Không biết cả thời lượng lẫn dung lượng thì dùng AI_API_TIMEOUT_SECONDS.
    """
    duration = job_duration_sec(job)
    size_mb = job_file_size_mb(job)
    if duration is None and size_mb is None:
        return settings.AI_API_TIMEOUT_SECONDS
    timeout = (
        settings.AI_TIMEOUT_BASE_SEC
        + settings.AI_TIMEOUT_PER_VIDEO_SEC * (duration or 0)
        + settings.AI_TIMEOUT_PER_MB_SEC * (size_mb or 0)
    )
    return min(timeout, settings.AI_TIMEOUT_MAX_SEC)
