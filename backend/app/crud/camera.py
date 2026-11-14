from typing import Optional
from bson import ObjectId

from app.crud.base import CRUDBase
from app.models.camera import Camera, CameraStatus
from app.schemas.camera import CameraCreate, CameraUpdate


class CRUDCamera(CRUDBase[Camera, CameraCreate, CameraUpdate]):
    def get_by_status(
        self,
        status: CameraStatus | str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Camera], int]:
        """Lấy danh sách camera theo trạng thái kết nối."""
        status_val = status.value if isinstance(status, CameraStatus) else str(status)
        return self.get_multi(filter={"status": status_val}, skip=skip, limit=limit)

    def update_status(
        self,
        camera_id: str | ObjectId,
        status: CameraStatus | str,
    ) -> Optional[Camera]:
        """Cập nhật trạng thái camera (online, offline, error)."""
        status_val = status.value if isinstance(status, CameraStatus) else str(status)
        return self.update(camera_id, {"status": status_val})


crud_camera = CRUDCamera(Camera)
