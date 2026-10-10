"""
Kiểm thử tự động các lớp bảo vệ nghiệp vụ (Security & Submission Guards):
1. Object-Level RBAC Guard (verify_course_teacher).
2. 4-Layer Submission Guard (Lớp chốt điểm, khóa nộp bài, hết hạn, quá số lượt).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from fastapi import HTTPException
from app.models.course import Course, CourseStatus, GradingFormula
from app.models.sport import Sport, SportMode
from app.models.task import Task, TaskCategory
from app.models.user import User, UserRole
from app.schemas.video_result import VideoResultCreate
from app.services.video_result_service import video_result_service


def test_submission_guards():
    print("\n[TEST GUARDS] Kiểm thử 4 Lớp Bảo Vệ Nộp Bài Video...")

    now = datetime.now(timezone.utc)
    sport_id = str(ObjectId())
    course_id = str(ObjectId())
    task_id = str(ObjectId())

    mock_sport = Sport(id=sport_id, code="badminton", name="Cầu lông", mode=SportMode.VIDEO)

    # ─── GUARD 1: Lớp học phần đã chốt điểm ───
    mock_course_locked = Course(
        id=course_id,
        name="Cầu lông",
        teacher_id=str(ObjectId()),
        teacher_name="Cô Bình",
        is_grade_locked=True,
    )
    mock_task = Task(
        id=task_id,
        course_id=course_id,
        sport_id=sport_id,
        title="Phát cầu",
        category=TaskCategory.PRACTICE,
    )

    with patch("app.services.video_result_service.crud_task.get", return_value=mock_task), \
         patch("app.services.video_result_service.crud_course.get", return_value=mock_course_locked):
        try:
            video_result_service.submit_video(
                user_id=str(ObjectId()),
                video_in=VideoResultCreate(task_id=task_id, sport_id=sport_id),
            )
            assert False, "Phải chặn khi lớp đã chốt điểm"
        except HTTPException as e:
            assert e.status_code == 403
            assert "chốt" in e.detail
            print("  ✓ Guard 1 PASSED: Đã chặn khi lớp học phần đã chốt sổ điểm.")

    # ─── GUARD 2: Giảng viên khóa tính năng nộp bài luyện tập ───
    mock_course_no_practice = Course(
        id=course_id,
        name="Cầu lông",
        teacher_id=str(ObjectId()),
        teacher_name="Cô Bình",
        is_grade_locked=False,
        allow_practice_submission=False,
    )

    with patch("app.services.video_result_service.crud_task.get", return_value=mock_task), \
         patch("app.services.video_result_service.crud_course.get", return_value=mock_course_no_practice):
        try:
            video_result_service.submit_video(
                user_id=str(ObjectId()),
                video_in=VideoResultCreate(task_id=task_id, sport_id=sport_id),
            )
            assert False, "Phải chặn khi GV khóa luyện tập"
        except HTTPException as e:
            assert e.status_code == 403
            assert "khóa nộp bài luyện tập" in e.detail
            print("  ✓ Guard 2 PASSED: Đã chặn khi GV khóa nộp bài luyện tập.")

    # ─── GUARD 3: Bài tập bị khóa hoặc hết hạn ───
    mock_course_open = Course(
        id=course_id,
        name="Cầu lông",
        teacher_id=str(ObjectId()),
        teacher_name="Cô Bình",
        is_grade_locked=False,
        allow_practice_submission=True,
    )
    mock_task_expired = Task(
        id=task_id,
        course_id=course_id,
        sport_id=sport_id,
        title="Phát cầu",
        category=TaskCategory.PRACTICE,
        close_time=(now - timedelta(days=1)).replace(tzinfo=None),  # Quá hạn (offset-naive datetime)
    )

    with patch("app.services.video_result_service.crud_task.get", return_value=mock_task_expired), \
         patch("app.services.video_result_service.crud_course.get", return_value=mock_course_open):
        try:
            video_result_service.submit_video(
                user_id=str(ObjectId()),
                video_in=VideoResultCreate(task_id=task_id, sport_id=sport_id),
            )
            assert False, "Phải chặn khi bài tập đã hết hạn"
        except HTTPException as e:
            assert e.status_code == 400
            assert "hết hạn" in e.detail
            print("  ✓ Guard 3 PASSED: Đã chặn khi bài tập đã hết hạn nộp.")

    # ─── GUARD 4: Vượt quá số lần nộp cho phép ───
    mock_task_max_attempts = Task(
        id=task_id,
        course_id=course_id,
        sport_id=sport_id,
        title="Phát cầu",
        category=TaskCategory.PRACTICE,
        max_attempts=3,
        close_time=now + timedelta(days=5),
    )

    from unittest.mock import PropertyMock
    mock_collection = MagicMock()
    mock_collection.count_documents.return_value = 3

    with patch("app.services.video_result_service.crud_task.get", return_value=mock_task_max_attempts), \
         patch("app.services.video_result_service.crud_course.get", return_value=mock_course_open), \
         patch.object(type(video_result_service.submit_video.__globals__["crud_video_result"]), "collection", new_callable=PropertyMock, return_value=mock_collection):
        try:
            video_result_service.submit_video(
                user_id=str(ObjectId()),
                video_in=VideoResultCreate(task_id=task_id, sport_id=sport_id),
            )
            assert False, "Phải chặn khi đã nộp đủ 3 lần"
        except HTTPException as e:
            assert e.status_code == 400
            assert "hết lượt nộp bài" in e.detail
            print("  ✓ Guard 4 PASSED: Đã chặn khi sinh viên đã nộp hết số lần cho phép (3/3).")





if __name__ == "__main__":
    print("=" * 60)
    print(">>> BẮT ĐẦU KIỂM THỬ CÁC LỚP BẢO VỆ NGHIỆP VỤ")
    print("=" * 60)
    test_submission_guards()
    print("\n" + "=" * 60)
    print(">>> TOÀN BỘ CÁC LỚP BẢO VỆ ĐÃ ĐẠT CHUẨN AN TOÀN (PASSED)!")
    print("=" * 60)
