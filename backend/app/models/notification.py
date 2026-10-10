from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional

from .base import BaseDocument


class NotificationType(str, Enum):
    GRADE_FINALIZED = "grade_finalized"
    GRADE_UNLOCKED = "grade_unlocked"
    SUBMISSION_GRADED = "submission_graded"
    SUBMISSION_RECEIVED = "submission_received"
    LOCK_TOGGLED = "lock_toggled"
    GENERAL = "general"


class Notification(BaseDocument):
    __collection__: ClassVar[str] = "notifications"

    user_id: str
    type: NotificationType = NotificationType.GENERAL
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
