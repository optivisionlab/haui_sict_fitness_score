from typing import Optional
from fastapi import HTTPException, status as http_status

from app.crud.camera import crud_camera
from app.models.camera import Camera, CameraStatus
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    def create_camera(self, camera_in: CameraCreate) -> Camera:
        """Thêm thiết bị camera mới."""
        return crud_camera.create(camera_in)

    def get_by_id(self, camera_id: str) -> Camera:
        """Lấy chi tiết camera."""
        camera = crud_camera.get(camera_id)
        if not camera:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy thiết bị camera",
            )
        return camera

    def list_cameras(
        self,
        camera_status: Optional[CameraStatus] = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs,
    ) -> tuple[list[Camera], int]:
        """Lấy danh sách camera."""
        # Backward compatibility for status parameter
        effective_status = camera_status or kwargs.get("status")
        if effective_status:
            return crud_camera.get_by_status(effective_status, skip=skip, limit=limit)
        return crud_camera.get_multi(skip=skip, limit=limit)

    def update_camera(self, camera_id: str, camera_in: CameraUpdate) -> Camera:
        """Cập nhật thông tin camera."""
        self.get_by_id(camera_id)
        updated = crud_camera.update(camera_id, camera_in)
        if not updated:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật camera thất bại",
            )
        return updated

    def update_status(self, camera_id: str, new_status: CameraStatus) -> Camera:
        """Cập nhật trạng thái camera (online/offline/error)."""
        self.get_by_id(camera_id)
        updated = crud_camera.update_status(camera_id, new_status)
        if not updated:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật trạng thái camera thất bại",
            )
        return updated

    def delete_camera(self, camera_id: str) -> bool:
        """Xóa camera."""
        self.get_by_id(camera_id)
        return crud_camera.delete(camera_id)


camera_service = CameraService()
