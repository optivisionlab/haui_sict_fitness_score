from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.task import crud_task
from app.crud.video_result import crud_video_result
from app.models.enrollment import Enrollment
from app.models.task import TaskCategory
from app.models.user import User
from app.schemas.student import StudentGradeViewResponse, StudentTaskGradeItem
from app.services.auth_service import get_current_user, verify_student_in_course

router = APIRouter(prefix="/student", tags=["Student Flow"])


@router.get("/courses/{course_id}/grades", response_model=StudentGradeViewResponse)
def get_student_course_grades(
    course_id: str,
    enrollment: Enrollment = Depends(verify_student_in_course),
    current_user: User = Depends(get_current_user),
):
    """Sinh viên xem bảng điểm chi tiết của môn học mình đã ghi danh."""
    course = crud_course.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học")

    tasks, _ = crud_task.get_by_course(course_id, limit=100)
    user_id = str(current_user.id)

    task_ids = [str(t.id) for t in tasks]
    
    # Lấy tất cả bài nộp của sinh viên cho các bài tập này trong 1 truy vấn (hạn chế N+1)
    video_results_cursor = crud_video_result.collection.find(
        {"taskId": {"$in": task_ids}, "userId": user_id},
    ).sort("submittedAt", -1)
    
    latest_subs = {}
    for doc in video_results_cursor:
        tid = doc["taskId"]
        if tid not in latest_subs:
            latest_subs[tid] = doc

    task_items = []
    for t in tasks:
        t_id = str(t.id)
        score = enrollment.task_scores.get(t_id)

        last_sub = latest_subs.get(t_id)

        sub_status = "not_submitted"
        submitted_at = None
        if last_sub:
            submitted_at = last_sub.get("submittedAt")
            sub_status = "pending" if last_sub.get("pending", True) else "graded"

        task_items.append(
            StudentTaskGradeItem(
                task_id=t_id,
                task_title=t.title,
                category=getattr(t, "category", TaskCategory.PRACTICE),
                score=score,
                submitted_at=submitted_at,
                status=sub_status,
            )
        )

    grades = enrollment.grades
    return StudentGradeViewResponse(
        course_name=course.name,
        teacher_name=course.teacher_name,
        is_grade_locked=enrollment.is_grade_locked,
        progress_percent=enrollment.progress_percent,
        attendance_score=grades.attendance_score,
        process_score=grades.process_score,
        exam_score=grades.exam_score,
        final_score=grades.final_score,
        letter_grade=grades.letter_grade,
        is_passed=grades.is_passed,
        tasks=task_items,
    )
