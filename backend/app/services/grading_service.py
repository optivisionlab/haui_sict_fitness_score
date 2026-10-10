import math
from typing import Optional

from app.models.course import GradingFormula
from app.models.enrollment import StudentGrades


class GradingService:
    """
    Dịch vụ tính toán điểm số theo chuẩn quy chế đào tạo tín chỉ:
    - Tính điểm quá trình từ các bài tập (Practice tasks)
    - Tính điểm tổng kết hệ 10 theo tỷ trọng học phần (Attendance, Practice, Exam)
    - Quy đổi điểm chữ (A, B+, B, C+, C, D+, D, F) và xét Đạt/Trượt
    """

    @staticmethod
    def calculate_letter_grade(final_score: float) -> tuple[str, bool]:
        """
        Quy đổi điểm hệ 10 sang thang điểm chữ chuẩn tín chỉ:
        - 8.5 - 10.0: A (Đạt)
        - 8.0 - 8.4:  B+ (Đạt)
        - 7.0 - 7.9:  B (Đạt)
        - 6.5 - 6.9:  C+ (Đạt)
        - 5.5 - 6.4:  C (Đạt)
        - 5.0 - 5.4:  D+ (Đạt)
        - 4.0 - 4.9:  D (Đạt)
        - Dưới 4.0:   F (Trượt)
        """
        score = round(final_score, 2)
        if score >= 8.5:
            return "A", True
        elif score >= 8.0:
            return "B+", True
        elif score >= 7.0:
            return "B", True
        elif score >= 6.5:
            return "C+", True
        elif score >= 5.5:
            return "C", True
        elif score >= 5.0:
            return "D+", True
        elif score >= 4.0:
            return "D", True
        else:
            return "F", False

    @classmethod
    def compute_student_grades(
        cls,
        current_grades: StudentGrades,
        task_scores: dict[str, float],
        practice_task_ids: list[str],
        formula: GradingFormula,
        exam_score_override: Optional[float] = None,
    ) -> StudentGrades:
        """
        Tính toán lại toàn bộ cấu trúc điểm của sinh viên dựa trên điểm các bài tập và công thức tỷ trọng.
        """
        # 1. Tính điểm quá trình (process_score) = Trung bình cộng các bài practice đã có điểm
        practice_scores = [
            task_scores[t_id] for t_id in practice_task_ids if t_id in task_scores and task_scores[t_id] is not None
        ]
        if practice_scores:
            process_score = round(sum(practice_scores) / len(practice_scores), 2)
        else:
            process_score = current_grades.process_score

        # 2. Điểm chuyên cần (attendance_score)
        attendance_score = current_grades.attendance_score

        # 3. Điểm thi kết thúc học phần (exam_score)
        exam_score = exam_score_override if exam_score_override is not None else current_grades.exam_score

        # 4. Tính điểm tổng kết (final_score) nếu có đủ thông tin
        final_score = None
        letter_grade = None
        is_passed = None

        w_att = formula.attendance_weight
        w_prc = formula.practice_weight
        w_exm = formula.exam_weight

        # Nếu có điểm thi thì tính được điểm tổng kết
        if exam_score is not None:
            eff_att = attendance_score if attendance_score is not None else 0.0
            eff_prc = process_score if process_score is not None else 0.0
            total = eff_att * w_att + eff_prc * w_prc + exam_score * w_exm
            final_score = round(total, 2)
            letter_grade, is_passed = cls.calculate_letter_grade(final_score)

        return StudentGrades(
            attendance_score=attendance_score,
            process_score=process_score,
            exam_score=exam_score,
            final_score=final_score,
            letter_grade=letter_grade,
            is_passed=is_passed,
        )


grading_service = GradingService()
