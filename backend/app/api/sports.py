import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.sport import SportMode
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.sport import SportCreate, SportRead, SportUpdate
from app.services.auth_service import require_roles
from app.services.sport_service import sport_service

router = APIRouter(prefix="/sports", tags=["Sports"])


@router.post("", response_model=SportRead, status_code=status.HTTP_201_CREATED)
def create_sport(
    sport_in: SportCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Thêm môn thể thao mới (chỉ Admin)."""
    sport = sport_service.create_sport(sport_in)
    return SportRead.model_validate(sport)


@router.get("", response_model=PaginatedResponse[SportRead])
def list_sports(
    mode: Optional[SportMode] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Lấy danh sách các môn thể thao (lọc theo mode video hoặc camera)."""
    skip = (page - 1) * page_size
    items, total = sport_service.list_sports(mode=mode, skip=skip, limit=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[SportRead](
        items=[SportRead.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/definitions")
def get_sport_definitions():
    """
    Lấy danh sách các môn thể thao và tiêu chí chỉ số đo lường (metrics fields, formula, thresholds).
    Phục vụ giao diện Frontend hiển thị linh hoạt khi giáo viên tạo bài tập hoặc tra cứu barem chấm điểm.
    """
    return sport_service.get_definitions()


@router.post("/sync-definitions", response_model=MessageResponse)
def sync_sport_definitions(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Đồng bộ các môn thể thao từ SPORT_DEFINITIONS vào cơ sở dữ liệu MongoDB (chỉ Admin)."""
    synced = sport_service.sync_sports_from_definitions()
    return MessageResponse(
        message=f"Đã đồng bộ thành công {len(synced)} môn thể thao mới vào cơ sở dữ liệu"
    )


@router.get("/{sport_id}", response_model=SportRead)
def get_sport(sport_id: str):
    """Xem chi tiết môn thể thao và scoring config."""
    sport = sport_service.get_by_id(sport_id)
    return SportRead.model_validate(sport)


@router.put("/{sport_id}", response_model=SportRead)
def update_sport(
    sport_id: str,
    sport_in: SportUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Cập nhật thông tin môn thể thao hoặc tiêu chí chấm điểm (chỉ Admin)."""
    sport = sport_service.update_sport(sport_id, sport_in)
    return SportRead.model_validate(sport)


@router.delete("/{sport_id}", response_model=MessageResponse)
def delete_sport(
    sport_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Xóa môn thể thao (chỉ Admin)."""
    sport_service.delete_sport(sport_id)
    return MessageResponse(message=f"Đã xóa môn thể thao {sport_id} thành công")
