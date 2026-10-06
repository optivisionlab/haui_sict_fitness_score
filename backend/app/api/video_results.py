import math
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.video_result import (
    PresignedUrlResponse,
    VideoResultAIUpdate,
    VideoResultCreate,
    VideoResultRead,
    VideoResultStatusResponse,
    VideoResultTeacherGrade,
)
from app.services.auth_service import get_current_user, require_roles, verify_internal_api_key
from app.services.video_result_service import video_result_service

router = APIRouter(prefix="/video-results", tags=["Video Results"])


@router.post("/upload", response_model=VideoResultRead, status_code=status.HTTP_201_CREATED)
def upload_video(
    file: UploadFile = File(...),
    task_id: Optional[str] = Form(None),
    exercise_id: Optional[str] = Form(None),
    sport_id: Optional[str] = Form(None),
    course_id: Optional[str] = Form(None),
    class_id: Optional[str] = Form(None),
    student_id: Optional[str] = Form(None),
    duration_sec: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """Sinh viên nộp bài tập bằng cách tải file video trực tiếp lên MinIO (có 4 lớp kiểm tra bảo vệ)."""
    db = get_db()
    actual_task_id = task_id or exercise_id
    c_id = course_id or class_id

    # Nếu task_id dạng alias ('tx1', 'tx2', 'task-0', 'midterm') hoặc không phải ObjectId hợp lệ
    if actual_task_id and not ObjectId.is_valid(actual_task_id) and c_id:
        course_tasks = list(db.tasks.find({"courseId": str(c_id)}).sort("createdAt", 1))
        if course_tasks:
            alias = actual_task_id.lower()
            if "tx1" in alias or alias == "task-0":
                actual_task_id = str(course_tasks[0]["_id"])
            elif "tx2" in alias or alias == "task-1":
                idx = min(1, len(course_tasks) - 1)
                actual_task_id = str(course_tasks[idx]["_id"])
            elif "midterm" in alias or alias == "task-2":
                idx = min(2, len(course_tasks) - 1)
                actual_task_id = str(course_tasks[idx]["_id"])
            elif "final" in alias:
                actual_task_id = str(course_tasks[-1]["_id"])
            else:
                actual_task_id = str(course_tasks[0]["_id"])

    if not actual_task_id or not ObjectId.is_valid(actual_task_id):
        # Thử tìm task đầu tiên nếu có course_id
        if c_id:
            first_task = db.tasks.find_one({"courseId": str(c_id)})
            if first_task:
                actual_task_id = str(first_task["_id"])

    if not actual_task_id:
        raise HTTPException(status_code=400, detail="Thiếu task_id hoặc exercise_id hợp lệ")

    actual_sport_id = sport_id
    if not actual_sport_id:
        task_doc = db.tasks.find_one({"_id": ObjectId(actual_task_id)}) if ObjectId.is_valid(actual_task_id) else None
        sport_id_val = None
        if task_doc:
            sport_id_val = task_doc.get("sportId") or task_doc.get("sport_id")
        if sport_id_val:
            actual_sport_id = str(sport_id_val)
        else:
            sport_doc = db.sports.find_one({"mode": "video"})
            if not sport_doc:
                raise HTTPException(
                    status_code=400,
                    detail="Không thể xác định môn thể thao tương ứng với bài tập này",
                )
            actual_sport_id = str(sport_doc["_id"])

    result = video_result_service.submit_video_file(
        user_id=str(current_user.id),
        task_id=actual_task_id,
        sport_id=actual_sport_id,
        file=file,
        duration_sec=duration_sec,
    )
    return VideoResultRead.model_validate(result)


@router.post("/submit", response_model=VideoResultRead, status_code=status.HTTP_201_CREATED)
def submit_video(
    video_in: VideoResultCreate,
    current_user: User = Depends(get_current_user),
):
    """Sinh viên nộp video bài tập qua URL có sẵn (có 4 lớp kiểm tra bảo vệ)."""
    user_id = str(current_user.id)
    result = video_result_service.submit_video(user_id=user_id, video_in=video_in)
    return VideoResultRead.model_validate(result)


@router.get("/{result_id}/video-url", response_model=PresignedUrlResponse)
@router.get("/{result_id}/presigned-url", response_model=PresignedUrlResponse, include_in_schema=False)
def get_presigned_url(
    result_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lấy presigned URL tạm thời để xem hoặc tải video từ MinIO."""
    url = video_result_service.get_presigned_url(
        result_id=result_id,
        current_user_id=str(current_user.id),
        role=str(current_user.role.value if hasattr(current_user.role, "value") else current_user.role),
    )
    return PresignedUrlResponse(video_url=url, expires_in_seconds=7200)


@router.get("/{result_id}/status", response_model=VideoResultStatusResponse)
@router.get("/status/{result_id}", response_model=VideoResultStatusResponse, include_in_schema=False)
def get_submission_status(
    result_id: str,
    current_user: User = Depends(get_current_user),
):
    """Kiểm tra trạng thái bài nộp (Status Polling siêu nhẹ < 15ms)."""
    return video_result_service.get_status(result_id)


@router.get("", response_model=PaginatedResponse[VideoResultRead])
def list_video_results(
    task_id: Optional[str] = None,
    exercise_id: Optional[str] = None,
    user_id: Optional[str] = None,
    student_id: Optional[str] = None,
    pending: Optional[bool] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các bài nộp video (hỗ trợ lọc theo task, sinh viên, trạng thái pending)."""
    actual_task_id = task_id or exercise_id
    actual_user_id = user_id or student_id
    if current_user.role == UserRole.STUDENT:
        actual_user_id = str(current_user.id)

    actual_pending = pending
    if status_filter:
        if status_filter in ["pending", "processing"]:
            actual_pending = True
        elif status_filter in ["completed", "graded"]:
            actual_pending = False

    skip = (page - 1) * page_size
    items, total = video_result_service.list_results(
        task_id=actual_task_id, user_id=actual_user_id, pending=actual_pending, skip=skip, limit=page_size
    )
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return PaginatedResponse[VideoResultRead](
        items=[VideoResultRead.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{result_id}", response_model=VideoResultRead)
def get_video_result(
    result_id: str,
    current_user: User = Depends(get_current_user),
):
    """Xem chi tiết một bài nộp video và kết quả AI/GV chấm."""
    result = video_result_service.get_by_id(result_id)
    return VideoResultRead.model_validate(result)


@router.post("/{result_id}/ai-callback", response_model=VideoResultRead)
def ai_callback(
    result_id: str,
    ai_in: VideoResultAIUpdate,
    _authorized: bool = Depends(verify_internal_api_key),
):
    """Endpoint dành cho AI Worker gửi kết quả phân tích và điểm tự động."""
    result = video_result_service.ai_callback(result_id, ai_in)
    return VideoResultRead.model_validate(result)


@router.post("/{result_id}/grade", response_model=VideoResultRead)
def teacher_grade(
    result_id: str,
    grade_in: VideoResultTeacherGrade,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Giáo viên chấm điểm thủ công hoặc sửa điểm AI."""
    result = video_result_service.teacher_grade(
        result_id=result_id,
        teacher_id=str(current_user.id),
        grade_in=grade_in,
    )
    return VideoResultRead.model_validate(result)
