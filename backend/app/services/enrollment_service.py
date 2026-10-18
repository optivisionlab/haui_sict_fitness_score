from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.task import crud_task
from app.crud.user import crud_user
from app.models.enrollment import Enrollment, EnrollmentStatus, StudentGrades
from app.models.task import TaskCategory
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate
from app.schemas.teacher import SingleGradeUpdate
from app.services.grading_service import grading_service


class EnrollmentService:
    def enroll(self, enrollment_in: EnrollmentCreate) -> Enrollment:
        """Đăng ký khóa học cho sinh viên và denormalize thông tin cá nhân."""
        # Kiểm tra user
        user = crud_user.get(enrollment_in.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy người dùng ID {enrollment_in.user_id}",
            )

        # Kiểm tra course
        course = crud_course.get(enrollment_in.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khóa học ID {enrollment_in.course_id}",
            )

        # Kiểm tra đã đăng ký chưa
        if crud_enrollment.is_enrolled(enrollment_in.user_id, enrollment_in.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sinh viên đã đăng ký khóa học này trước đó",
            )

        # Chuẩn bị dữ liệu denormalized
        data = enrollment_in.model_dump(by_alias=True, exclude_unset=True)
        data["courseName"] = course.name
        data["teacherName"] = course.teacher_name
        data["examDate"] = course.exam_date
        data["status"] = EnrollmentStatus.ACTIVE.value
        data["progressPercent"] = 0.0
        data["completedTaskIds"] = []
        data["taskScores"] = {}

        # Denormalize thông tin sinh viên để sổ điểm load siêu nhanh
        data["studentCode"] = user.user_code or ""
        data["studentName"] = user.name
        data["studentEmail"] = user.email
        data["studentGender"] = getattr(user, "gender", None)

        # Cấu trúc điểm khởi tạo
        data["grades"] = StudentGrades().model_dump(by_alias=True)
        data["isGradeLocked"] = False

        created = crud_enrollment.create(data)

        # Tăng sĩ số lớp
        crud_course.increment_student_total(enrollment_in.course_id, amount=1)
        return created

    def get_by_id(self, enrollment_id: str) -> Enrollment:
        """Lấy chi tiết bản ghi ghi danh."""
        enrollment = crud_enrollment.get(enrollment_id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy bản ghi ghi danh",
            )
        return enrollment

    def get_student_enrollments(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Enrollment], int]:
        """Lấy danh sách các môn sinh viên đang học."""
        return crud_enrollment.get_by_user(user_id, status=status, skip=skip, limit=limit)

    def get_course_enrollments(
        self,
        course_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Enrollment], int]:
        """Lấy danh sách sinh viên đăng ký khóa học."""
        return crud_enrollment.get_by_course(course_id, status=status, skip=skip, limit=limit)

    def cancel_enrollment(self, enrollment_id: str) -> bool:
        """Hủy ghi danh khóa học."""
        enrollment = self.get_by_id(enrollment_id)
        if enrollment.is_grade_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể hủy ghi danh vì điểm học phần đã bị khóa",
            )
        if enrollment.status == EnrollmentStatus.DONE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể hủy ghi danh khóa học đã hoàn thành",
            )
        success = crud_enrollment.delete(enrollment_id)
        if success:
            crud_course.increment_student_total(enrollment.course_id, amount=-1)
        return success

    def update_task_progress(self, user_id: str, task_id: str, score: float) -> Optional[Enrollment]:
        """Đồng bộ điểm và tiến độ học tập vào Enrollment khi sinh viên đạt điểm một task."""
        task = crud_task.get(task_id)
        if not task:
            return None

        enrollment = crud_enrollment.get_by_user_and_course(user_id, task.course_id)
        if not enrollment:
            return None

        course = crud_course.get(task.course_id)
        if not course:
            return None

        # Tính % tiến độ dựa trên các tasks thuộc môn học
        tasks_in_course, _ = crud_task.get_by_course(task.course_id, limit=200)
        total_tasks = len(tasks_in_course)

        completed_set = set(enrollment.completed_task_ids)
        completed_set.add(str(task_id))

        progress = round((len(completed_set) / total_tasks * 100.0), 1) if total_tasks > 0 else 100.0
        if progress > 100.0:
            progress = 100.0

        updated = crud_enrollment.record_task_completion(
            enrollment_id=enrollment.id,
            task_id=str(task_id),
            score=score,
            progress_percent=progress,
        )

        # Tính lại toàn bộ điểm tổng kết theo công thức (Ripple effect)
        if updated:
            self.recalculate_student_grades(updated, course, tasks_in_course)
        return updated

    def recalculate_student_grades(
        self,
        enrollment: Enrollment,
        course,
        tasks_in_course: list,
    ) -> Optional[Enrollment]:
        """Tính lại điểm quá trình, điểm thi và điểm tổng kết cho sinh viên."""
        practice_task_ids = [str(t.id) for t in tasks_in_course if getattr(t, "category", TaskCategory.PRACTICE) == TaskCategory.PRACTICE]
        exam_tasks = [t for t in tasks_in_course if getattr(t, "category", TaskCategory.PRACTICE) == TaskCategory.EXAM]

        exam_score = None
        if exam_tasks:
            # Lấy điểm bài exam đầu tiên tìm thấy
            exam_t_id = str(exam_tasks[0].id)
            if exam_t_id in enrollment.task_scores:
                exam_score = enrollment.task_scores[exam_t_id]

        new_grades = grading_service.compute_student_grades(
            current_grades=enrollment.grades,
            task_scores=enrollment.task_scores,
            practice_task_ids=practice_task_ids,
            formula=course.grading_formula,
            exam_score_override=exam_score,
        )

        return crud_enrollment.update_grades_data(
            enrollment_id=enrollment.id,
            grades_dict=new_grades.model_dump(by_alias=True),
        )

    def batch_update_grades(
        self,
        course_id: str,
        updates: list[SingleGradeUpdate],
    ) -> int:
        """Giáo viên cập nhật điểm chuyên cần, điểm thi hoặc ghi chú hàng loạt."""
        course = crud_course.get(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Không tìm thấy khóa học")

        if course.is_grade_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lớp học phần đã chốt sổ điểm, không thể chỉnh sửa điểm",
            )

        tasks_in_course, _ = crud_task.get_by_course(course_id, limit=200)
        practice_task_ids = [str(t.id) for t in tasks_in_course if getattr(t, "category", TaskCategory.PRACTICE) == TaskCategory.PRACTICE]

        enrollment_ids = [ObjectId(item.enrollment_id) for item in updates if ObjectId.is_valid(item.enrollment_id)]
        enrollments_cursor = crud_enrollment.collection.find({"_id": {"$in": enrollment_ids}})
        enrollment_map = {str(doc["_id"]): crud_enrollment.model.model_validate(doc) for doc in enrollments_cursor}

        updated_count = 0
        for item in updates:
            enrollment = enrollment_map.get(item.enrollment_id)
            if not enrollment or str(enrollment.course_id) != str(course_id):
                continue

            current_grades = enrollment.grades
            if item.attendance_score is not None:
                current_grades.attendance_score = item.attendance_score

            exam_override = item.exam_score if item.exam_score is not None else current_grades.exam_score

            computed_grades = grading_service.compute_student_grades(
                current_grades=current_grades,
                task_scores=enrollment.task_scores,
                practice_task_ids=practice_task_ids,
                formula=course.grading_formula,
                exam_score_override=exam_override,
            )

            crud_enrollment.update_grades_data(
                enrollment_id=enrollment.id,
                grades_dict=computed_grades.model_dump(by_alias=True),
                note=item.note if item.note is not None else enrollment.note,
            )
            updated_count += 1

        return updated_count


enrollment_service = EnrollmentService()
