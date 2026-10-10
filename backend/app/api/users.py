import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserRead, UserUpdate
from app.services.auth_service import get_current_user, require_roles
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserRead])
def list_users(
    role: Optional[UserRole] = None,
    page: int = Query(default=1, ge=1, description="Số trang"),
    page_size: int = Query(default=10, ge=1, le=100, description="Số bản ghi mỗi trang"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Lấy danh sách người dùng có phân trang (chỉ Admin/Giáo viên)."""
    skip = (page - 1) * page_size
    items, total = user_service.get_users(role=role, skip=skip, limit=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[UserRead](
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một người dùng."""
    user = user_service.get_by_id(user_id)
    return UserRead.model_validate(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
):
    """Cập nhật thông tin người dùng (chính chủ hoặc Admin)."""
    if current_user.role != UserRole.ADMIN and str(current_user.id) != str(user_id):
        user_in.role = None  # Không cho phép tự nâng quyền

    updated = user_service.update_profile(user_id, user_in)
    return UserRead.model_validate(updated)


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Xóa người dùng (chỉ Admin)."""
    user_service.delete_user(user_id)
    return MessageResponse(message=f"Đã xóa người dùng {user_id} thành công")
