import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.task import TaskCreate, TaskLockUpdate, TaskRead, TaskUpdate
from app.schemas.video_result import SubmissionItemResponse
from app.services.auth_service import require_roles
from app.services.task_service import task_service
from app.services.video_result_service import video_result_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Tạo bài tập / bài thi mới (Admin hoặc Giáo viên)."""
    task = task_service.create_task(task_in)
    return task_service.to_read_dto(task)


@router.get("", response_model=PaginatedResponse[TaskRead])
def list_tasks(
    course_id: Optional[str] = None,
    sport_id: Optional[str] = None,
    category: Optional[str] = Query(default=None, description="practice | exam | all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    """Lấy danh sách các bài tập / bài thi theo khóa học hoặc môn thể thao."""
    skip = (page - 1) * page_size
    items, total = task_service.list_tasks(
        course_id=course_id,
        sport_id=sport_id,
        category=category,
        skip=skip,
        limit=page_size,
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[TaskRead](
        items=[task_service.to_read_dto(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: str):
    """Xem chi tiết bài tập/bài thi."""
    task = task_service.get_by_id(task_id)
    return task_service.to_read_dto(task)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Cập nhật bài tập / bài thi (Admin hoặc Giáo viên)."""
    task = task_service.update_task(task_id, task_in)
    return task_service.to_read_dto(task)


@router.patch("/{task_id}/lock", response_model=TaskRead)
def toggle_task_lock(
    task_id: str,
    lock_in: TaskLockUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Khóa / Mở khóa nhanh một bài tập cụ thể."""
    task = task_service.toggle_lock(task_id, lock_in.is_locked)
    return task_service.to_read_dto(task)


@router.get("/{task_id}/submissions", response_model=list[SubmissionItemResponse])
def get_task_submissions(
    task_id: str,
    status: Optional[str] = Query(default=None, description="pending | ai_graded | teacher_graded"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Lấy danh sách các bài nộp của một bài tập / bài kiểm tra."""
    return video_result_service.list_task_submissions(task_id=task_id, status_filter=status)


@router.delete("/{task_id}", response_model=MessageResponse)
def delete_task(
    task_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Xóa bài tập (Admin hoặc Giáo viên)."""
    task_service.delete_task(task_id)
    return MessageResponse(message=f"Đã xóa bài tập {task_id} thành công")
