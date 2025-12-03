from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from enum import Enum

if TYPE_CHECKING:
    from app.models.user import User, UserClass
    from app.models.classes import Class


class CameraStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"



class CameraUserClass(SQLModel, table=True):
    __tablename__ = "camera_user_class"
    __table_args__ = (
        UniqueConstraint("camera_id", "user_id", "class_id", "time_id", name="uix_cam_user_class_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    camera_id: int = Field(
        sa_column=Column(ForeignKey("cameras.camera_id", ondelete="CASCADE", onupdate="CASCADE"))
    )
    user_id: int = Field(
        sa_column=Column(ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"))
    )
    class_id: Optional[int] = Field(
        sa_column=Column(ForeignKey("classes.class_id", ondelete="SET NULL", onupdate="CASCADE"))
    )
    time_id: int = Field(default=datetime.utcnow().timestamp())

    lap: int = Field(default=1)
    avg_speed: Optional[float] = Field(default=None)
    checkin_time: Optional[datetime] = Field(default=None)
    flag: Optional[str] = Field(default=None, max_length=50)
    image_url: Optional[str] = Field(default=None, max_length=500)

    # Relationships
    camera: "Camera" = Relationship(back_populates="camera_user_classes")
    user: "User" = Relationship(back_populates="camera_user_classes")
    class_: Optional["Class"] = Relationship(back_populates="camera_user_classes")

class CameraBase(SQLModel):
    camera_name: str = Field(max_length=255)
    camera_location: Optional[str] = Field(max_length=255, default=None)
    camera_ip: Optional[str] = Field(max_length=50, default=None)
    camera_url: Optional[str] = Field(max_length=500, default=None)
    camera_status: CameraStatus = Field(default=CameraStatus.active)
    description: Optional[str] = None


class Camera(CameraBase, table=True):
    __tablename__ = "cameras"
    
    camera_id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # relationship to CameraUserClass (checkin records)
    camera_user_classes: List[CameraUserClass] = Relationship(back_populates="camera")
