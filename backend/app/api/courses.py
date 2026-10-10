import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    WeekCreate,
    WeekUpdate,
)
from app.services.auth_service import get_current_user, require_roles
from app.services.course_service import course_service

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(
    course_in: CourseCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Tạo mới một khóa học (Admin hoặc Giáo viên)."""
    # Nếu giáo viên tạo thì tự động gán teacher_id là ID của chính mình nếu chưa chỉ định
    if current_user.role == UserRole.TEACHER and not course_in.teacher_id:
        course_in.teacher_id = str(current_user.id)

    course = course_service.create_course(course_in)
    return CourseRead.model_validate(course)


@router.get("", response_model=PaginatedResponse[CourseRead])
def list_courses(
    teacher_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Lấy danh sách khóa học có phân trang."""
    skip = (page - 1) * page_size
    items, total = course_service.list_courses(teacher_id=teacher_id, skip=skip, limit=page_size)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[CourseRead](
        items=[CourseRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: str):
    """Xem chi tiết khóa học và danh sách tuần học."""
    course = course_service.get_by_id(course_id)
    return CourseRead.model_validate(course)


@router.put("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: str,
    course_in: CourseUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Cập nhật thông tin khóa học."""
    course = course_service.update_course(course_id, course_in)
    return CourseRead.model_validate(course)


@router.delete("/{course_id}", response_model=MessageResponse)
def delete_course(
    course_id: str,
    force: bool = Query(default=False, description="Bắt buộc xóa kèm cascade toàn bộ task và enrollment liên quan"),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Xóa khóa học (Admin)."""
    course_service.delete_course(course_id, force=force)
    return MessageResponse(message=f"Đã xóa khóa học {course_id} thành công")


# ─── Quản lý Weeks của Course ───────────────────────────────────────────────

@router.post("/{course_id}/weeks", response_model=CourseRead)
def add_week(
    course_id: str,
    week_in: WeekCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Thêm một tuần học vào khóa học."""
    course = course_service.add_week(course_id, week_in)
    return CourseRead.model_validate(course)


@router.put("/{course_id}/weeks/{week_order}", response_model=CourseRead)
def update_week(
    course_id: str,
    week_order: int,
    week_in: WeekUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Cập nhật tuần học theo số thứ tự tuần (week_order)."""
    course = course_service.update_week(course_id, week_order, week_in)
    return CourseRead.model_validate(course)


@router.delete("/{course_id}/weeks/{week_order}", response_model=CourseRead)
def delete_week(
    course_id: str,
    week_order: int,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Xóa một tuần học khỏi khóa học."""
    course = course_service.delete_week(course_id, week_order)
    return CourseRead.model_validate(course)
