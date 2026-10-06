from datetime import datetime
from typing import Optional

from app.models.base import PyObjectId
from app.models.notification import NotificationType
from app.schemas.common import BaseSchema


class NotificationRead(BaseSchema):
    id: PyObjectId
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None


class NotificationCreate(BaseSchema):
    user_id: str
    type: NotificationType = NotificationType.GENERAL
    title: str
    message: str
    link: Optional[str] = None
