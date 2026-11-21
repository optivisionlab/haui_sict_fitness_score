from datetime import datetime, timezone
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
        from app.services.grade_calculator import recalculate_enrollment
        return recalculate_enrollment(enrollment, course, tasks_in_course)

    def batch_update_grades(
        self,
        course_id: str,
        updates: list[SingleGradeUpdate],
    ) -> int:
        """GV cập nhật điểm chuyên cần, điểm thi cuối kỳ hoặc ghi chú hàng loạt."""
        from app.models.task import TaskKind, task_kind
        from app.services.grade_calculator import attendance_scores_for_course, recalculate_enrollment

        course = crud_course.get(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Không tìm thấy khóa học")

        if course.is_grade_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lớp học phần đã chốt sổ điểm, không thể chỉnh sửa điểm",
            )

        tasks_in_course, _ = crud_task.get_by_course(course_id, limit=200)
        final_tasks = [t for t in tasks_in_course if task_kind(t) == TaskKind.FINAL]
        attendance_map = attendance_scores_for_course(course_id)
        if attendance_map is not None and any(item.attendance_score is not None for item in updates):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lớp đang dùng điểm danh theo buổi, điểm chuyên cần được tính tự động",
            )

        enrollment_ids = [ObjectId(item.enrollment_id) for item in updates if ObjectId.is_valid(item.enrollment_id)]
        enrollments_cursor = crud_enrollment.collection.find({"_id": {"$in": enrollment_ids}})
        enrollment_map = {str(doc["_id"]): crud_enrollment.model.model_validate(doc) for doc in enrollments_cursor}

        updated_count = 0
        for item in updates:
            enrollment = enrollment_map.get(item.enrollment_id)
            if not enrollment or str(enrollment.course_id) != str(course_id):
                continue

            set_fields: dict = {"updatedAt": datetime.now(timezone.utc)}
            if item.attendance_score is not None:
                set_fields["grades.attendanceScore"] = item.attendance_score
            if item.exam_score is not None:
                if not final_tasks:
                    raise HTTPException(status_code=400, detail="Lớp chưa có bài thi kết thúc học phần")
                set_fields[f"taskScoreOverrides.{final_tasks[0].id}"] = item.exam_score
            if item.note is not None:
                set_fields["note"] = item.note
            crud_enrollment.collection.update_one({"_id": ObjectId(enrollment.id)}, {"$set": set_fields})

            fresh = crud_enrollment.get(enrollment.id)
            recalculate_enrollment(fresh, course, tasks_in_course, attendance_map)
            updated_count += 1

        return updated_count

    def set_task_score_override(
        self, course_id: str, enrollment_id: str, task_id: str, score: Optional[float]
    ) -> Enrollment:
        """GV nhập tay (hoặc xóa, score=None) điểm một bài cho một sinh viên."""
        from app.services.grade_calculator import recalculate_enrollment

        course = crud_course.get(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Không tìm thấy khóa học")
        if course.is_grade_locked:
            raise HTTPException(status_code=400, detail="Lớp học phần đã chốt sổ điểm, không thể chỉnh sửa điểm")
        task = crud_task.get(task_id)
        enrollment = crud_enrollment.get(enrollment_id)
        if not task or str(task.course_id) != str(course_id):
            raise HTTPException(status_code=404, detail="Bài kiểm tra không thuộc lớp này")
        if not enrollment or str(enrollment.course_id) != str(course_id):
            raise HTTPException(status_code=404, detail="Sinh viên không thuộc lớp này")

        key = f"taskScoreOverrides.{task_id}"
        update = {"$unset": {key: ""}} if score is None else {"$set": {key: score}}
        update.setdefault("$set", {})["updatedAt"] = datetime.now(timezone.utc)
        crud_enrollment.collection.update_one({"_id": ObjectId(enrollment.id)}, update)
        return recalculate_enrollment(crud_enrollment.get(enrollment.id), course)


enrollment_service = EnrollmentService()
