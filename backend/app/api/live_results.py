import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.live_result import (
    LiveResultCreate,
    LiveResultFinishRequest,
    LiveResultRead,
    LiveResultUpdate,
)
from app.services.auth_service import get_current_user, require_roles, verify_internal_api_key
from app.services.live_result_service import live_result_service

router = APIRouter(prefix="/live-results", tags=["Live Results"])


@router.post("/start", response_model=LiveResultRead, status_code=status.HTTP_201_CREATED)
def start_session(
    live_in: LiveResultCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Bắt đầu phiên thi trực tiếp qua camera tại sân."""
    session = live_result_service.start_session(live_in)
    return LiveResultRead.model_validate(session)


@router.get("", response_model=PaginatedResponse[LiveResultRead])
def list_live_results(
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    camera_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các lượt thi trực tiếp qua camera."""
    if current_user.role == UserRole.STUDENT:
        user_id = str(current_user.id)

    skip = (page - 1) * page_size
    items, total = live_result_service.list_results(
        task_id=task_id, user_id=user_id, camera_id=camera_id, skip=skip, limit=page_size
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[LiveResultRead](
        items=[LiveResultRead.model_validate(lr) for lr in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{result_id}", response_model=LiveResultRead)
def get_live_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
):
    """Xem chi tiết một lượt thi trực tiếp."""
    result = live_result_service.get_by_id(result_id)
    return LiveResultRead.model_validate(result)


@router.put("/{result_id}", response_model=LiveResultRead)
def update_live_metrics(
    result_id: str,
    update_in: LiveResultUpdate,
    _authorized: bool = Depends(verify_internal_api_key),
):
    """Camera / AI streaming service cập nhật metrics thời gian thực."""
    result = live_result_service.update_session(result_id, update_in)
    return LiveResultRead.model_validate(result)


@router.post("/{result_id}/finish", response_model=LiveResultRead)
def finish_session(
    result_id: str,
    finish_in: Optional[LiveResultFinishRequest] = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Đánh dấu kết thúc phiên thi, chốt điểm và cập nhật tiến độ học tập."""
    score = finish_in.score if finish_in else None
    metrics = finish_in.metrics if finish_in else None
    result = live_result_service.finish_session(result_id, score=score, metrics=metrics)
    return LiveResultRead.model_validate(result)
