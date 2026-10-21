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


def compute_ai_timeout(job: dict[str, Any]) -> float:
    """Timeout gọi AI tỉ lệ theo thời lượng video, có trần AI_TIMEOUT_MAX_SEC."""
    duration = job_duration_sec(job)
    if duration is None:
        return settings.AI_API_TIMEOUT_SECONDS
    return min(
        settings.AI_TIMEOUT_BASE_SEC + settings.AI_TIMEOUT_PER_VIDEO_SEC * duration,
        settings.AI_TIMEOUT_MAX_SEC,
    )
