from datetime import datetime
from typing import Optional

from app.models.base import PyObjectId
from app.models.camera import CameraStatus
from app.schemas.common import BaseSchema


class CameraBase(BaseSchema):
    name: str
    location: Optional[str] = None
    stream_url: str
    status: CameraStatus = CameraStatus.OFFLINE


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseSchema):
    name: Optional[str] = None
    location: Optional[str] = None
    stream_url: Optional[str] = None
    status: Optional[CameraStatus] = None


class CameraStatusUpdate(BaseSchema):
    status: CameraStatus


class CameraRead(BaseSchema):
    id: PyObjectId
    name: str
    location: Optional[str] = None
    stream_url: str
    status: CameraStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
