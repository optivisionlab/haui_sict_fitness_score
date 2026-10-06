import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.camera import CameraStatus
from app.models.user import User, UserRole
from app.schemas.camera import CameraCreate, CameraRead, CameraStatusUpdate, CameraUpdate
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.auth_service import require_roles
from app.services.camera_service import camera_service

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera(
    camera_in: CameraCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Thêm thiết bị camera mới (Admin)."""
    camera = camera_service.create_camera(camera_in)
    return CameraRead.model_validate(camera)


@router.get("", response_model=PaginatedResponse[CameraRead])
def list_cameras(
    status_filter: Optional[CameraStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Lấy danh sách camera trường học (lọc theo online/offline/error)."""
    skip = (page - 1) * page_size
    items, total = camera_service.list_cameras(status=status_filter, skip=skip, limit=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[CameraRead](
        items=[CameraRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: str):
    """Xem chi tiết camera và luồng stream."""
    camera = camera_service.get_by_id(camera_id)
    return CameraRead.model_validate(camera)


@router.put("/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: str,
    camera_in: CameraUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Cập nhật thông tin camera (Admin)."""
    camera = camera_service.update_camera(camera_id, camera_in)
    return CameraRead.model_validate(camera)


@router.put("/{camera_id}/status", response_model=CameraRead)
def update_camera_status(
    camera_id: str,
    status_in: CameraStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Cập nhật nhanh trạng thái camera."""
    camera = camera_service.update_status(camera_id, status_in.status)
    return CameraRead.model_validate(camera)


@router.delete("/{camera_id}", response_model=MessageResponse)
def delete_camera(
    camera_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Xóa camera (Admin)."""
    camera_service.delete_camera(camera_id)
    return MessageResponse(message=f"Đã xóa thiết bị camera {camera_id} thành công")
