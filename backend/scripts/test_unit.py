"""
Bộ Test Unit tự động kiểm thử toàn diện nghiệp vụ Clean Code:
1. Kiểm thử Quy tắc tính điểm tín chỉ & quy đổi điểm chữ (GradingService).
2. Kiểm thử Strategy Pattern mở rộng môn thể thao (SportEvaluatorRegistry).
3. Kiểm thử Khả năng đăng ký môn mới linh hoạt (Extensibility verification).
4. Kiểm thử DTO Schemas & CamelCase Serializer.
"""

import sys
from pathlib import Path

# Đảm bảo in UTF-8 không bị lỗi trên Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Đảm bảo import được module app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from app.models.course import GradingFormula
from app.models.enrollment import StudentGrades
from app.models.task import TaskCategory
from app.schemas.course import CourseRead
from app.schemas.teacher import GradebookResponse, GradebookStudentItem, GradebookTaskItem
from app.services.grading_service import grading_service
from app.services.sports.base import BaseSportEvaluator
from app.services.sports.registry import sport_registry


def test_grading_service():
    print("\n[TEST 1] Kiểm thử GradingService...")
    # 1. Kiểm thử quy đổi điểm chữ
    assert grading_service.calculate_letter_grade(9.0) == ("A", True)
    assert grading_service.calculate_letter_grade(8.2) == ("B+", True)
    assert grading_service.calculate_letter_grade(7.5) == ("B", True)
    assert grading_service.calculate_letter_grade(6.7) == ("C+", True)
    assert grading_service.calculate_letter_grade(5.8) == ("C", True)
    assert grading_service.calculate_letter_grade(5.2) == ("D+", True)
    assert grading_service.calculate_letter_grade(4.5) == ("D", True)
    assert grading_service.calculate_letter_grade(3.5) == ("F", False)
    print("  ✓ Quy đổi điểm chữ đạt chuẩn tín chỉ.")

    # 2. Kiểm thử tính điểm tổng kết theo trọng số
    formula = GradingFormula(attendance_weight=0.2, practice_weight=0.3, exam_weight=0.5)
    current_grades = StudentGrades(attendance_score=9.0)
    task_scores = {"task_p1": 8.0, "task_p2": 9.0}
    practice_ids = ["task_p1", "task_p2"]

    computed = grading_service.compute_student_grades(
        current_grades=current_grades,
        task_scores=task_scores,
        practice_task_ids=practice_ids,
        formula=formula,
        exam_score_override=8.0,
    )

    # Process score = (8.0 + 9.0) / 2 = 8.5
    assert computed.process_score == 8.5
    # Final = 9.0*0.2 + 8.5*0.3 + 8.0*0.5 = 1.8 + 2.55 + 4.0 = 8.35
    assert computed.final_score == 8.35
    assert computed.letter_grade == "B+"
    assert computed.is_passed is True
    print(f"  ✓ Tính điểm tổng kết chính xác: {computed.final_score} ({computed.letter_grade}).")


def test_sport_evaluator_registry():
    print("\n[TEST 2] Kiểm thử Strategy & Registry Pattern Môn Thể Thao...")
    pickleball = sport_registry.get_evaluator("pickleball")
    assert pickleball.sport_code == "PICKLEBALL"

    # Test tính điểm Pickleball
    metrics = {"swingTotal": 100, "hitCount": 85, "hitRate": 0.85}
    score = pickleball.calculate_score(metrics)
    assert 0.0 <= score <= 10.0
    comment = pickleball.generate_comment(metrics, score)
    assert len(comment) > 0 and score > 0.0
    print(f"  ✓ Đánh giá Pickleball: {score}đ - '{comment}'")

    running = sport_registry.get_evaluator("running")
    assert running.sport_code == "RUNNING"
    r_metrics = {"durationSec": 350, "formScore": 8.5}
    r_score = running.calculate_score(r_metrics)
    assert r_score == 9.7  # 10.0 * 0.8 + 8.5 * 0.2 = 9.7
    print(f"  ✓ Đánh giá Chạy bền: {r_score}đ.")



def test_extensibility_adding_new_sport():
    print("\n[TEST 3] Kiểm thử Khả Năng Mở Rộng Thêm Môn Mới (Open/Closed Principle)...")

    # Giả lập lập trình viên tạo thêm môn Bóng Rổ (Basketball)
    class BasketballEvaluator(BaseSportEvaluator):
        @property
        def sport_code(self) -> str:
            return "BASKETBALL"

        @property
        def sport_name(self) -> str:
            return "Bóng rổ"

        def validate_metrics(self, metrics):
            return True, None

        def calculate_score(self, metrics, criteria=None):
            # Tỷ lệ ném rổ trúng * 10
            shots = metrics.get("shots", 10)
            goals = metrics.get("goals", 7)
            return round((goals / shots) * 10.0, 2)

        def generate_comment(self, metrics, score):
            return f"Kỹ thuật ném rổ đạt {score} điểm."

    # Đăng ký môn mới vào registry
    sport_registry.register(BasketballEvaluator())

    # Lấy ra sử dụng ngay lập tức
    bb = sport_registry.get_evaluator("BASKETBALL")
    assert bb.sport_code == "BASKETBALL"
    bb_score = bb.calculate_score({"shots": 10, "goals": 9})
    assert bb_score == 9.0
    print(f"  ✓ Môn mới (Bóng rổ) đã được thêm và hoạt động trơn tru: {bb_score}đ!")


def test_schemas_and_serialization():
    print("\n[TEST 4] Kiểm thử Schemas & CamelCase Serialization...")
    gradebook = GradebookResponse(
        course_id="64b1c2d3e4f5a6789012bcde",
        is_grade_locked=False,
        formula=GradingFormula(attendance_weight=0.2, practice_weight=0.3, exam_weight=0.5),
        task_list=[GradebookTaskItem(id="t1", title="Phát cầu", category=TaskCategory.PRACTICE)],
        students=[
            GradebookStudentItem(
                enrollment_id="e1",
                user_id="u1",
                student_code="SV001",
                student_name="Nguyen Van A",
                progress_percent=80.0,
            )
        ],
    )

    dumped = gradebook.model_dump(by_alias=True)
    assert "courseId" in dumped
    assert "isGradeLocked" in dumped
    assert "taskList" in dumped
    assert "students" in dumped
    assert dumped["students"][0]["studentCode"] == "SV001"
    print("  ✓ Unified Response contract tuân thủ camelCase chuẩn xác 100%.")


if __name__ == "__main__":
    print("=" * 60)
    print(">>> BẮT ĐẦU CHẠY BỘ TEST UNIT NGHIỆP VỤ CLEAN CODE")
    print("=" * 60)
    test_grading_service()
    test_sport_evaluator_registry()
    test_extensibility_adding_new_sport()
    test_schemas_and_serialization()
    print("\n" + "=" * 60)
    print(">>> TOÀN BỘ 4 BỘ TEST ĐÃ VƯỢT QUA (100% PASSED)!")
    print("=" * 60)
