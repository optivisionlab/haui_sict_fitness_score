"""Tính điểm học phần thể chất theo một quy tắc duy nhất.

Điểm tổng kết = Chuyên cần × w1 + Quá trình × w2 + Thi × w3   (mặc định 0.1 / 0.3 / 0.6)

- Quá trình: trung bình các bài thường xuyên (TX) và thi giữa kỳ đã có điểm.
- Thi: điểm bài thi kết thúc học phần (nhiều bài cuối kỳ thì lấy trung bình).
- Chuyên cần: tính từ điểm danh nếu lớp có buổi điểm danh, ngược lại dùng điểm GV nhập.
- Điểm từng bài: điểm GV nhập tay (override) ưu tiên hơn điểm tính từ bài nộp.
- Điều kiện dự thi: chuyên cần và quá trình đạt ngưỡng GV cấu hình.

Mọi nơi làm thay đổi điểm (AI chấm, GV chấm/nhập, điểm danh, đổi tỷ trọng, chốt điểm)
đều gọi recalculate_enrollment / recalculate_course để kết quả luôn nhất quán.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId

from app.core.database import get_db
from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.task import crud_task
from app.models.enrollment import StudentGrades
from app.models.task import TaskKind, task_kind
from app.services.grading_service import grading_service

# Trọng số trạng thái điểm danh khi quy ra điểm chuyên cần (thang 10)
ATTENDANCE_WEIGHTS = {"present": 1.0, "late": 0.5, "excused": 0.5, "absent": 0.0}
ATTENDANCE_COLLECTION = "attendance_sessions"


def _avg(values: list[float]) -> Optional[float]:
    return round(sum(values) / len(values), 2) if values else None


def attendance_scores_for_course(course_id: str) -> Optional[dict[str, float]]:
    """Điểm chuyên cần theo user_id tính từ các buổi điểm danh; None nếu lớp chưa điểm danh buổi nào.

    Sinh viên không có bản ghi trong một buổi (vd ghi danh sau buổi đó) không bị tính buổi đó.
    """
    sessions = list(get_db()[ATTENDANCE_COLLECTION].find({"courseId": str(course_id)}, {"records": 1}))
    if not sessions:
        return None
    totals: dict[str, list[float]] = {}
    for session in sessions:
        for user_id, state in (session.get("records") or {}).items():
            totals.setdefault(user_id, []).append(ATTENDANCE_WEIGHTS.get(state, 0.0))
    return {uid: round(sum(v) / len(v) * 10, 2) for uid, v in totals.items() if v}


def compute_grades(
    enrollment: Any,
    course: Any,
    tasks: list,
    attendance_map: Optional[dict[str, float]] = None,
    missing_exam_as_zero: bool = False,
) -> StudentGrades:
    task_scores: dict[str, float] = dict(enrollment.task_scores or {})
    task_scores.update(getattr(enrollment, "task_score_overrides", None) or {})

    process_values, exam_values = [], []
    for task in tasks:
        score = task_scores.get(str(task.id))
        if score is None:
            continue
        if task_kind(task) == TaskKind.FINAL:
            exam_values.append(float(score))
        else:
            process_values.append(float(score))

    process_score = _avg(process_values)
    exam_score = _avg(exam_values)
    has_final_task = any(task_kind(t) == TaskKind.FINAL for t in tasks)
    if exam_score is None and missing_exam_as_zero and has_final_task:
        exam_score = 0.0

    if attendance_map is not None:
        attendance_score = attendance_map.get(str(enrollment.user_id))
    else:
        attendance_score = enrollment.grades.attendance_score

    rule = course.exam_eligibility
    is_eligible = True
    if rule.enabled:
        is_eligible = (
            (attendance_score or 0.0) >= rule.min_attendance_score
            and (process_score or 0.0) >= rule.min_process_score
        )

    final_score = letter_grade = is_passed = None
    if exam_score is not None:
        f = course.grading_formula
        total = (
            (attendance_score or 0.0) * f.attendance_weight
            + (process_score or 0.0) * f.practice_weight
            + exam_score * f.exam_weight
        )
        final_score = round(total, 2)
        letter_grade, is_passed = grading_service.calculate_letter_grade(final_score)
        if not is_eligible:
            # Không đủ điều kiện dự thi thì không đạt học phần
            letter_grade, is_passed = "F", False

    return StudentGrades(
        attendance_score=attendance_score,
        process_score=process_score,
        exam_score=exam_score,
        final_score=final_score,
        letter_grade=letter_grade,
        is_passed=is_passed,
        is_eligible=is_eligible,
    )


def recalculate_enrollment(enrollment: Any, course: Any = None, tasks: Optional[list] = None,
                           attendance_map: Any = "auto", missing_exam_as_zero: bool = False):
    course = course or crud_course.get(enrollment.course_id)
    if course is None:
        return None
    if tasks is None:
        tasks, _ = crud_task.get_by_course(enrollment.course_id, limit=200)
    if attendance_map == "auto":
        attendance_map = attendance_scores_for_course(str(course.id))
    grades = compute_grades(enrollment, course, tasks, attendance_map, missing_exam_as_zero)
    return crud_enrollment.update_grades_data(
        enrollment_id=enrollment.id, grades_dict=grades.model_dump(by_alias=True)
    )


def recalculate_course(course_id: str) -> int:
    """Tính lại điểm toàn bộ sinh viên của lớp (sau khi đổi tỷ trọng, điểm danh, sửa bài...)."""
    course = crud_course.get(course_id)
    if course is None:
        return 0
    tasks, _ = crud_task.get_by_course(course_id, limit=200)
    attendance_map = attendance_scores_for_course(course_id)
    count = 0
    for doc in crud_enrollment.collection.find({"courseId": str(course_id)}):
        recalculate_enrollment(crud_enrollment.model.model_validate(doc), course, tasks, attendance_map)
        count += 1
    return count


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_oid(value: str) -> Optional[ObjectId]:
    return ObjectId(value) if ObjectId.is_valid(value) else None
