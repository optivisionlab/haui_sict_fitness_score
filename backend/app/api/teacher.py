from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.course import Course
from app.models.user import User, UserRole
from app.schemas.course import SubmissionLockUpdate
from app.schemas.task import TaskRead
from app.schemas.teacher import (
    BatchGradeUpdateRequest,
    BatchGradeUpdateResponse,
    CourseStatsResponse,
    FinalizeGradesRequest,
    FinalizeGradesResponse,
    GradebookResponse,
    SubmissionLockResponse,
    TeacherCourseDetail,
    TeacherCourseItem,
    UnlockGradesRequest,
    UnlockGradesResponse,
)
from app.services.auth_service import get_current_user, require_roles, verify_course_teacher
from app.services.course_service import course_service
from app.services.enrollment_service import enrollment_service
from app.services.task_service import task_service

router = APIRouter(prefix="/teacher", tags=["Teacher Portal"])


@router.get("/courses", response_model=list[TeacherCourseItem])
def get_teacher_courses(
    status: Optional[str] = Query(default="all", description="in_progress | completed | all"),
    search: Optional[str] = Query(default=None, description="Tìm theo tên hoặc mã lớp"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Lấy danh sách các lớp học phần do giáo viên đang đăng nhập phụ trách."""
    teacher_id = str(current_user.id)
    return course_service.get_teacher_courses(
        teacher_id=teacher_id, status_filter=status, search=search
    )


@router.get("/courses/{course_id}", response_model=TeacherCourseDetail)
def get_teacher_course_detail(
    course: Course = Depends(verify_course_teacher),
):
    """Chi tiết một lớp học phần kèm tỷ trọng điểm và thống kê bài tập."""
    return course_service.get_teacher_course_detail(str(course.id))


@router.patch("/courses/{course_id}/submission-lock", response_model=SubmissionLockResponse)
def update_submission_lock(
    lock_in: SubmissionLockUpdate,
    course: Course = Depends(verify_course_teacher),
):
    """Khóa / Mở tính năng nộp bài luyện tập và bài kiểm tra ở cấp độ lớp."""
    return course_service.update_submission_lock(
        course_id=str(course.id),
        allow_practice=lock_in.allow_practice_submission,
        allow_exam=lock_in.allow_exam_submission,
    )


@router.get("/courses/{course_id}/gradebook", response_model=GradebookResponse)
def get_course_gradebook(
    search: Optional[str] = Query(default=None, description="Tìm theo MSSV hoặc họ tên"),
    status: Optional[str] = Query(default="all", description="active | dropped | all"),
    course: Course = Depends(verify_course_teacher),
):
    """Lấy toàn bộ sổ điểm lớp học phần (1 query duy nhất, không phân trang)."""
    return course_service.get_course_gradebook(
        course_id=str(course.id), search=search, status_filter=status
    )


@router.put("/courses/{course_id}/grades", response_model=BatchGradeUpdateResponse)
def update_grades(
    batch_in: BatchGradeUpdateRequest,
    course: Course = Depends(verify_course_teacher),
):
    """Cập nhật điểm thành phần thủ công (chuyên cần, thi kết thúc, ghi chú) hàng loạt."""
    count = enrollment_service.batch_update_grades(
        course_id=str(course.id), updates=batch_in.updates
    )
    return BatchGradeUpdateResponse(updated_count=count)


@router.post("/courses/{course_id}/finalize-grades", response_model=FinalizeGradesResponse)
def finalize_grades(
    req: FinalizeGradesRequest,
    course: Course = Depends(verify_course_teacher),
    current_user: User = Depends(get_current_user),
):
    """Chốt sổ điểm lớp học phần chính thức và đóng băng quyền nộp bài / sửa điểm."""
    return course_service.finalize_grades(
        course_id=str(course.id),
        teacher_id=str(current_user.id),
        confirm=req.confirm,
        final_remarks=req.final_remarks,
        force=req.force,
    )


@router.post("/courses/{course_id}/unlock-grades", response_model=UnlockGradesResponse)
def unlock_grades(
    req: UnlockGradesRequest,
    course: Course = Depends(verify_course_teacher),
):
    """Mở khóa sổ điểm lớp học phần để điều chỉnh điểm hoặc phúc khảo."""
    return course_service.unlock_grades(course_id=str(course.id), reason=req.reason)


@router.get("/courses/{course_id}/stats", response_model=CourseStatsResponse)
def get_course_stats(
    course: Course = Depends(verify_course_teacher),
):
    """Thống kê kết quả học tập lớp, tỷ lệ qua môn và phổ điểm A-F."""
    return course_service.get_course_stats(str(course.id))


@router.get("/courses/{course_id}/tasks", response_model=list[TaskRead])
def get_course_tasks(
    category: Optional[str] = Query(default="all", description="practice | exam | all"),
    course: Course = Depends(verify_course_teacher),
):
    """Lấy danh sách các bài tập / bài thi của lớp học phần."""
    tasks, _ = task_service.list_tasks(
        course_id=str(course.id), category=category, limit=100
    )
    return [task_service.to_read_dto(t) for t in tasks]
