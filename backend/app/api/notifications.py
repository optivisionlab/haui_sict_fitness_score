from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationRead
from app.services.auth_service import get_current_user
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách thông báo của người dùng hiện tại."""
    notifications = notification_service.get_user_notifications(
        user_id=str(current_user.id), unread_only=unread_only, limit=limit
    )
    return [NotificationRead.model_validate(n) for n in notifications]


@router.patch("/{notification_id}/read", response_model=MessageResponse)
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Đánh dấu thông báo đã đọc."""
    updated = notification_service.mark_read(notification_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo",
        )
    return MessageResponse(message="Đã đánh dấu thông báo là đã đọc")


@router.delete("/{notification_id}", response_model=MessageResponse)
def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Xóa thông báo của người dùng hiện tại."""
    success = notification_service.delete_notification(
        notification_id=notification_id, user_id=str(current_user.id)
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo hoặc bạn không có quyền xóa",
        )
    return MessageResponse(message="Đã xóa thông báo thành công")
