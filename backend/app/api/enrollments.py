import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.crud.enrollment import crud_enrollment
from app.models.enrollment import EnrollmentStatus
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead
from app.services.auth_service import get_current_user
from app.services.enrollment_service import enrollment_service

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
def enroll_course(
    enrollment_in: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
):
    """Ghi danh sinh viên vào khóa học (sinh viên tự đăng ký hoặc giáo viên/admin đăng ký hộ)."""
    if current_user.role == UserRole.STUDENT and str(current_user.id) != str(enrollment_in.user_id):
        enrollment_in.user_id = str(current_user.id)

    enrollment = enrollment_service.enroll(enrollment_in)
    return EnrollmentRead.model_validate(enrollment)


@router.get("/my-courses", response_model=PaginatedResponse[EnrollmentRead])
def get_my_courses(
    status_filter: Optional[EnrollmentStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các môn học mà người dùng hiện tại đang ghi danh."""
    skip = (page - 1) * page_size
    items, total = enrollment_service.get_student_enrollments(
        user_id=str(current_user.id),
        status=status_filter,
        skip=skip,
        limit=page_size,
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[EnrollmentRead](
        items=[EnrollmentRead.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("", response_model=PaginatedResponse[EnrollmentRead])
def list_enrollments(
    user_id: Optional[str] = None,
    course_id: Optional[str] = None,
    status_filter: Optional[EnrollmentStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách ghi danh có bộ lọc theo sinh viên hoặc lớp học."""
    skip = (page - 1) * page_size
    if course_id:
        items, total = enrollment_service.get_course_enrollments(
            course_id=course_id, status=status_filter, skip=skip, limit=page_size
        )
    elif user_id:
        items, total = enrollment_service.get_student_enrollments(
            user_id=user_id, status=status_filter, skip=skip, limit=page_size
        )
    else:
        items, total = crud_enrollment.get_multi(skip=skip, limit=page_size)

    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    return PaginatedResponse[EnrollmentRead](
        items=[EnrollmentRead.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
def get_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Xem chi tiết tiến độ học tập và điểm số của một lượt ghi danh."""
    enrollment = enrollment_service.get_by_id(enrollment_id)
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER) and str(enrollment.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem thông tin ghi danh của sinh viên khác",
        )
    return EnrollmentRead.model_validate(enrollment)


@router.delete("/{enrollment_id}", response_model=MessageResponse)
def cancel_enrollment(
    enrollment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Hủy ghi danh khóa học."""
    enrollment = enrollment_service.get_by_id(enrollment_id)
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER) and str(enrollment.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hủy ghi danh của sinh viên khác",
        )
    enrollment_service.cancel_enrollment(enrollment_id)
    return MessageResponse(message=f"Đã hủy ghi danh {enrollment_id} thành công")
