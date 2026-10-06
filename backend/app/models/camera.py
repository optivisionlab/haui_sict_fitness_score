from enum import Enum
from typing import ClassVar, Optional

from .base import BaseDocument


class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class Camera(BaseDocument):
    __collection__: ClassVar[str] = "cameras"

    name: str
    location: Optional[str] = None
    stream_url: str
    status: CameraStatus = CameraStatus.OFFLINE
