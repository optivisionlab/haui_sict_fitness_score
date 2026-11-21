"""API cho GV quản lý lớp mình phụ trách: cấu hình điểm, bài kiểm tra, duyệt bài nộp, điểm danh.

Mọi endpoint đều qua verify_course_teacher (GV chỉ thao tác lớp của mình, admin mọi lớp).
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.crud.enrollment import crud_enrollment
from app.crud.task import crud_task
from app.crud.video_result import crud_video_result
from app.models.course import Course
from app.models.task import category_for_kind
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.course import CourseGradingSettings
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate, TeacherTaskUpsert
from app.schemas.teacher import (
    AttendanceSessionRead,
    AttendanceSessionUpsert,
    TaskScoreOverride,
)
from app.schemas.video_result import SubmissionItemResponse, VideoResultRead, VideoResultTeacherGrade
from app.services.auth_service import get_current_user, verify_course_teacher
from app.services.enrollment_service import enrollment_service
from app.services.grade_calculator import ATTENDANCE_COLLECTION, ATTENDANCE_WEIGHTS, recalculate_course
from app.services.task_service import task_service
from app.services.video_result_service import video_result_service

router = APIRouter(prefix="/teacher", tags=["Teacher Portal"])


def _ensure_unlocked(course: Course) -> None:
    if course.is_grade_locked:
        raise HTTPException(status_code=400, detail="Lớp học phần đã chốt sổ điểm, không thể chỉnh sửa")


def _course_task(course: Course, task_id: str):
    task = crud_task.get(task_id)
    if not task or str(task.course_id) != str(course.id):
        raise HTTPException(status_code=404, detail="Bài kiểm tra không thuộc lớp này")
    return task


# ---------------------------------------------------------------- Cấu hình điểm

@router.put("/courses/{course_id}/grading-settings", response_model=MessageResponse)
def update_grading_settings(
    settings_in: CourseGradingSettings,
    course: Course = Depends(verify_course_teacher),
):
    """Đổi tỷ trọng điểm (tổng = 1) và điều kiện dự thi, rồi tính lại điểm cả lớp."""
    _ensure_unlocked(course)
    get_db().courses.update_one(
        {"_id": ObjectId(course.id)},
        {"$set": {
            "gradingFormula": settings_in.grading_formula.model_dump(by_alias=True),
            "examEligibility": settings_in.exam_eligibility.model_dump(by_alias=True),
            "updatedAt": datetime.now(timezone.utc),
        }},
    )
    count = recalculate_course(str(course.id))
    return MessageResponse(message=f"Đã cập nhật cấu hình điểm và tính lại điểm cho {count} sinh viên")


# ---------------------------------------------------------------- Bài kiểm tra

def _resolve_sport_id(course: Course) -> str:
    if course.sport_id:
        return str(course.sport_id)
    existing, _ = crud_task.get_by_course(str(course.id), limit=1)
    if existing:
        return str(existing[0].sport_id)
    raise HTTPException(status_code=400, detail="Lớp chưa gắn môn thể thao, vui lòng liên hệ quản trị viên")


def _validate_window(task_in: TeacherTaskUpsert) -> None:
    if task_in.open_time and task_in.close_time and task_in.close_time <= task_in.open_time:
        raise HTTPException(status_code=400, detail="Hạn nộp phải sau thời gian mở")


@router.post("/courses/{course_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_course_task(task_in: TeacherTaskUpsert, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    _validate_window(task_in)
    data = task_in.model_dump()
    data.update(
        course_id=str(course.id),
        sport_id=_resolve_sport_id(course),
        category=category_for_kind(task_in.kind),
    )
    task = task_service.create_task(TaskCreate(**data))
    recalculate_course(str(course.id))
    return task_service.to_read_dto(task)


@router.put("/courses/{course_id}/tasks/{task_id}", response_model=TaskRead)
def update_course_task(task_id: str, task_in: TeacherTaskUpsert, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    _course_task(course, task_id)
    _validate_window(task_in)
    data = task_in.model_dump()
    data["category"] = category_for_kind(task_in.kind)
    task = task_service.update_task(task_id, TaskUpdate(**data))
    recalculate_course(str(course.id))
    return task_service.to_read_dto(task)


@router.delete("/courses/{course_id}/tasks/{task_id}", response_model=MessageResponse)
def delete_course_task(task_id: str, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    _course_task(course, task_id)
    if crud_video_result.collection.count_documents({"taskId": str(task_id)}, limit=1):
        raise HTTPException(status_code=400, detail="Bài đã có sinh viên nộp, không thể xóa. Hãy khóa bài thay vì xóa.")
    task_service.delete_task(task_id)
    get_db().enrollments.update_many(
        {"courseId": str(course.id)},
        {"$unset": {f"taskScores.{task_id}": "", f"taskScoreOverrides.{task_id}": ""},
         "$pull": {"completedTaskIds": str(task_id)}},
    )
    recalculate_course(str(course.id))
    return MessageResponse(message="Đã xóa bài kiểm tra")


# ---------------------------------------------------------------- Duyệt bài nộp

@router.get("/courses/{course_id}/tasks/{task_id}/submissions", response_model=list[SubmissionItemResponse])
def list_task_submissions(task_id: str, course: Course = Depends(verify_course_teacher)):
    """Bài nộp kiểm tra của một bài (không gồm luyện tập), mới nhất trước."""
    _course_task(course, task_id)
    return video_result_service.list_task_submissions(task_id)


@router.post("/courses/{course_id}/submissions/{result_id}/grade", response_model=VideoResultRead)
def grade_submission(
    result_id: str,
    grade_in: VideoResultTeacherGrade,
    course: Course = Depends(verify_course_teacher),
    current_user: User = Depends(get_current_user),
):
    """GV xác nhận hoặc chỉnh điểm AI và nhận xét cho một bài nộp."""
    _ensure_unlocked(course)
    result = video_result_service.get_by_id(result_id)
    if str(result.course_id) != str(course.id):
        raise HTTPException(status_code=404, detail="Bài nộp không thuộc lớp này")
    updated = video_result_service.teacher_grade(result_id, str(current_user.id), grade_in)
    return VideoResultRead.model_validate(updated)


@router.put("/courses/{course_id}/task-scores", response_model=MessageResponse)
def override_task_score(body: TaskScoreOverride, course: Course = Depends(verify_course_teacher)):
    """Nhập tay điểm một bài cho một sinh viên (vd thi trực tiếp không quay video); score=null để xóa."""
    enrollment_service.set_task_score_override(str(course.id), body.enrollment_id, body.task_id, body.score)
    return MessageResponse(message="Đã cập nhật điểm")


# ---------------------------------------------------------------- Điểm danh

def _session_read(doc: dict) -> AttendanceSessionRead:
    return AttendanceSessionRead(id=str(doc["_id"]), date=doc["date"], title=doc.get("title"), records=doc.get("records") or {})


def _clean_records(course: Course, records: dict[str, str]) -> dict[str, str]:
    enrolled = {
        str(doc["userId"]) for doc in crud_enrollment.collection.find({"courseId": str(course.id)}, {"userId": 1})
    }
    invalid_state = {s for s in records.values() if s not in ATTENDANCE_WEIGHTS}
    if invalid_state:
        raise HTTPException(status_code=400, detail=f"Trạng thái điểm danh không hợp lệ: {', '.join(invalid_state)}")
    return {uid: state for uid, state in records.items() if uid in enrolled}


@router.get("/courses/{course_id}/attendance", response_model=list[AttendanceSessionRead])
def list_attendance(course: Course = Depends(verify_course_teacher)):
    cursor = get_db()[ATTENDANCE_COLLECTION].find({"courseId": str(course.id)}).sort("date", 1)
    return [_session_read(doc) for doc in cursor]


@router.post("/courses/{course_id}/attendance", response_model=AttendanceSessionRead, status_code=201)
def create_attendance(body: AttendanceSessionUpsert, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    now = datetime.now(timezone.utc)
    doc = {
        "courseId": str(course.id),
        "date": body.date,
        "title": body.title,
        "records": _clean_records(course, body.records),
        "createdAt": now,
        "updatedAt": now,
    }
    doc["_id"] = get_db()[ATTENDANCE_COLLECTION].insert_one(doc).inserted_id
    recalculate_course(str(course.id))
    return _session_read(doc)


@router.put("/courses/{course_id}/attendance/{session_id}", response_model=AttendanceSessionRead)
def update_attendance(session_id: str, body: AttendanceSessionUpsert, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Mã buổi điểm danh không hợp lệ")
    doc = get_db()[ATTENDANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(session_id), "courseId": str(course.id)},
        {"$set": {
            "date": body.date,
            "title": body.title,
            "records": _clean_records(course, body.records),
            "updatedAt": datetime.now(timezone.utc),
        }},
        return_document=True,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi điểm danh")
    recalculate_course(str(course.id))
    return _session_read(doc)


@router.delete("/courses/{course_id}/attendance/{session_id}", response_model=MessageResponse)
def delete_attendance(session_id: str, course: Course = Depends(verify_course_teacher)):
    _ensure_unlocked(course)
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Mã buổi điểm danh không hợp lệ")
    res = get_db()[ATTENDANCE_COLLECTION].delete_one({"_id": ObjectId(session_id), "courseId": str(course.id)})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Không tìm thấy buổi điểm danh")
    recalculate_course(str(course.id))
    return MessageResponse(message="Đã xóa buổi điểm danh")
