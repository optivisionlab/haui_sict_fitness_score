from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from pydantic import Field

from .base import BaseDocument


class LiveResult(BaseDocument):
    __collection__: ClassVar[str] = "live_results"

    task_id: str
    sport_id: str
    user_id: str
    camera_id: str

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None

    metrics: dict[str, Any] = Field(default_factory=dict)  # Schemaless (laps, speed, ...)
    score: Optional[float] = None
