from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status

from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.task import crud_task
from app.crud.user import crud_user
from app.models.course import Course, CourseStatus
from app.models.enrollment import EnrollmentStatus
from app.models.notification import NotificationType
from app.models.task import TaskCategory
from app.schemas.course import CourseCreate, CourseUpdate, WeekCreate, WeekUpdate
from app.schemas.teacher import (
    CourseStatsResponse,
    FinalizeGradesResponse,
    GradeDistribution,
    GradebookResponse,
    GradebookStudentItem,
    GradebookTaskItem,
    StudentGradesSchema,
    SubmissionLockResponse,
    TeacherCourseDetail,
    TeacherCourseItem,
    UnlockGradesResponse,
)
from app.services.grading_service import grading_service
from app.services.notification_service import notification_service


class CourseService:
    def create_course(self, course_in: CourseCreate) -> Course:
        """Tạo mới khóa học, tự động đồng bộ tên giảng viên nếu chưa truyền."""
        course_data = course_in.model_dump(by_alias=True, exclude_unset=True)

        # Kiểm tra giáo viên
        teacher = crud_user.get(course_in.teacher_id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy giáo viên với ID {course_in.teacher_id}",
            )
        course_data["teacherName"] = teacher.name

        # Kiểm tra key/slug unique nếu có
        if course_in.key:
            existing_key = crud_course.get_by_key(course_in.key)
            if existing_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã định danh key '{course_in.key}' đã tồn tại",
                )

        return crud_course.create(course_data)

    def get_by_id(self, course_id: str) -> Course:
        """Lấy chi tiết khóa học."""
        course = crud_course.get(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy khóa học",
            )
        return course

    def update_course(self, course_id: str, course_in: CourseUpdate) -> Course:
        """Cập nhật thông tin khóa học."""
        self.get_by_id(course_id)
        update_data = course_in.model_dump(by_alias=True, exclude_unset=True)

        if "teacherId" in update_data and update_data["teacherId"]:
            teacher = crud_user.get(update_data["teacherId"])
            if not teacher:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Không tìm thấy giáo viên với ID {update_data['teacherId']}",
                )
            update_data["teacherName"] = teacher.name

        updated = crud_course.update(course_id, update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật khóa học thất bại",
            )
        return updated

    def delete_course(self, course_id: str, force: bool = False) -> bool:
        """Xóa khóa học và dọn dẹp các task/enrollment liên quan."""
        self.get_by_id(course_id)

        _, total_enr = crud_enrollment.get_by_course(course_id, limit=1)
        if total_enr > 0 and not force:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể xóa khóa học vì đang có {total_enr} sinh viên ghi danh. Vui lòng hoàn tất học phần hoặc sử dụng force=true.",
            )

        # Cascade xóa enrollments và tasks liên quan
        crud_enrollment.collection.delete_many({"courseId": str(course_id)})
        crud_task.collection.delete_many({"courseId": str(course_id)})

        return crud_course.delete(course_id)

    def list_courses(
        self,
        teacher_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Course], int]:
        """Lấy danh sách khóa học."""
        if teacher_id:
            return crud_course.get_by_teacher(teacher_id, skip=skip, limit=limit)
        return crud_course.get_multi(skip=skip, limit=limit)

    def add_week(self, course_id: str, week_in: WeekCreate) -> Course:
        """Thêm 1 tuần học mới vào khóa học."""
        course = self.get_by_id(course_id)
        if any(w.order == week_in.order for w in course.weeks):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tuần thứ {week_in.order} đã tồn tại trong khóa học",
            )
        updated = crud_course.add_week(course_id, week_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thêm tuần học thất bại",
            )
        return updated

    def update_week(self, course_id: str, week_order: int, week_in: WeekUpdate) -> Course:
        """Cập nhật thông tin tuần học."""
        self.get_by_id(course_id)
        updated = crud_course.update_week(course_id, week_order, week_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy tuần thứ {week_order} để cập nhật",
            )
        return updated

    def delete_week(self, course_id: str, week_order: int) -> Course:
        """Xóa một tuần học."""
        self.get_by_id(course_id)
        updated = crud_course.delete_week(course_id, week_order)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Xóa tuần thứ {week_order} thất bại",
            )
        return updated

    # ─── Teacher Portal Features ──────────────────────────────────────────────

    def get_teacher_courses(
        self,
        teacher_id: str,
        status_filter: Optional[str] = "all",
        search: Optional[str] = None,
    ) -> list[TeacherCourseItem]:
        """Lấy danh sách các lớp học phần do giáo viên phụ trách."""
        query: dict = {"teacherId": str(teacher_id)}
        if status_filter and status_filter != "all":
            query["status"] = status_filter
        if search:
            query["$or"] = [
                {"name": {"$regex": search.strip(), "$options": "i"}},
                {"code": {"$regex": search.strip(), "$options": "i"}},
            ]

        docs = crud_course.collection.find(query).sort("createdAt", -1)
        result = []
        for d in docs:
            course_obj = Course.model_validate(d)
            result.append(
                TeacherCourseItem(
                    id=course_obj.id,
                    code=course_obj.code,
                    name=course_obj.name,
                    student_total=course_obj.student_total,
                    status=course_obj.status,
                    is_grade_locked=course_obj.is_grade_locked,
                    allow_practice_submission=course_obj.allow_practice_submission,
                    allow_exam_submission=course_obj.allow_exam_submission,
                    start_date=course_obj.start_date,
                    end_date=course_obj.end_date,
                    exam_date=course_obj.exam_date,
                )
            )
        return result

    def get_teacher_course_detail(self, course_id: str) -> TeacherCourseDetail:
        """Lấy chi tiết lớp học phần cho giáo viên kèm tổng số tuần và tasks."""
        course = self.get_by_id(course_id)
        tasks, total_tasks = crud_task.get_by_course(course_id, limit=1)

        return TeacherCourseDetail(
            id=course.id,
            code=course.code,
            name=course.name,
            desc=course.desc,
            teacher_id=course.teacher_id,
            teacher_name=course.teacher_name,
            student_total=course.student_total,
            status=course.status,
            is_grade_locked=course.is_grade_locked,
            grade_locked_at=course.grade_locked_at,
            allow_practice_submission=course.allow_practice_submission,
            allow_exam_submission=course.allow_exam_submission,
            grading_formula=course.grading_formula,
            start_date=course.start_date,
            end_date=course.end_date,
            exam_date=course.exam_date,
            total_weeks=len(course.weeks),
            total_tasks=total_tasks,
        )

    def update_submission_lock(
        self,
        course_id: str,
        allow_practice: Optional[bool] = None,
        allow_exam: Optional[bool] = None,
    ) -> SubmissionLockResponse:
        """Khóa hoặc mở tính năng nộp bài luyện tập / thi ở cấp độ lớp."""
        course = self.get_by_id(course_id)
        update_dict: dict = {"updatedAt": datetime.now(timezone.utc)}

        if allow_practice is not None:
            update_dict["allowPracticeSubmission"] = allow_practice
        if allow_exam is not None:
            update_dict["allowExamSubmission"] = allow_exam

        crud_course.collection.update_one({"_id": ObjectId(course_id)}, {"$set": update_dict})
        refreshed = self.get_by_id(course_id)

        return SubmissionLockResponse(
            course_id=str(course_id),
            allow_practice_submission=refreshed.allow_practice_submission,
            allow_exam_submission=refreshed.allow_exam_submission,
            updated_at=datetime.now(timezone.utc),
        )

    def get_course_gradebook(
        self,
        course_id: str,
        search: Optional[str] = None,
        status_filter: Optional[str] = "all",
    ) -> GradebookResponse:
        """
        Lấy toàn bộ sổ điểm lớp học phần trong 1 TRUY VẤN DUY NHẤT (không dùng $lookup).
        """
        course = self.get_by_id(course_id)

        # Lấy danh sách tasks thuộc khóa học
        tasks_in_course, _ = crud_task.get_by_course(course_id, limit=100)
        task_list = [
            GradebookTaskItem(
                id=str(t.id),
                title=t.title,
                category=getattr(t, "category", TaskCategory.PRACTICE),
            )
            for t in tasks_in_course
        ]

        # Query enrollments
        enrollment_query: dict = {"courseId": str(course_id)}
        if status_filter and status_filter != "all":
            enrollment_query["status"] = status_filter
        if search:
            enrollment_query["$or"] = [
                {"studentName": {"$regex": search.strip(), "$options": "i"}},
                {"studentCode": {"$regex": search.strip(), "$options": "i"}},
            ]

        cursor = crud_enrollment.collection.find(enrollment_query).sort("studentCode", 1)
        students = []
        for doc in cursor:
            grades_raw = doc.get("grades") or {}
            try:
                grades_val = StudentGradesSchema.model_validate(grades_raw) if isinstance(grades_raw, dict) else StudentGradesSchema()
            except Exception:
                grades_val = StudentGradesSchema()

            students.append(
                GradebookStudentItem(
                    enrollment_id=str(doc["_id"]),
                    user_id=str(doc.get("userId", "")),
                    student_code=doc.get("studentCode"),
                    student_name=doc.get("studentName"),
                    student_email=doc.get("studentEmail"),
                    gender=doc.get("studentGender"),
                    status=doc.get("status", EnrollmentStatus.ACTIVE.value),
                    progress_percent=doc.get("progressPercent", 0.0),
                    task_scores=doc.get("taskScores", {}),
                    grades=grades_val,
                    note=doc.get("note"),
                )
            )

        return GradebookResponse(
            course_id=str(course_id),
            is_grade_locked=course.is_grade_locked,
            formula=course.grading_formula,
            task_list=task_list,
            students=students,
        )

    def finalize_grades(
        self,
        course_id: str,
        teacher_id: str,
        confirm: bool = True,
        final_remarks: Optional[str] = None,
        force: bool = False,
    ) -> FinalizeGradesResponse:
        """
        Chốt điểm chính thức cho lớp học phần:
        - Tính toán điểm tổng kết cho tất cả sinh viên
        - Đóng băng quyền sửa điểm trên lớp học và tất cả enrollments
        - Gửi thông báo đến sinh viên
        """
        course = self.get_by_id(course_id)
        if course.is_grade_locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lớp học phần này đã được chốt điểm trước đó",
            )

        tasks_in_course, _ = crud_task.get_by_course(course_id, limit=100)
        practice_ids = [str(t.id) for t in tasks_in_course if getattr(t, "category", TaskCategory.PRACTICE) == TaskCategory.PRACTICE]
        exam_tasks = [t for t in tasks_in_course if getattr(t, "category", TaskCategory.PRACTICE) == TaskCategory.EXAM]

        enrollments = list(crud_enrollment.collection.find({"courseId": str(course_id), "status": "active"}))
        if not enrollments:
            raise HTTPException(status_code=400, detail="Không có sinh viên nào trong lớp để chốt điểm")

        # Kiểm tra điều kiện: sinh viên có thiếu điểm thi hay không
        missing_exam_students = []
        if exam_tasks and not force:
            for enr in enrollments:
                task_scores = enr.get("taskScores", {})
                grades_exam = enr.get("grades", {}).get("examScore")
                has_exam_score = grades_exam is not None or any(str(et.id) in task_scores for et in exam_tasks)
                if not has_exam_score:
                    missing_exam_students.append(enr.get("studentCode") or str(enr["_id"]))

            if missing_exam_students:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Không thể chốt điểm: Vẫn còn {len(missing_exam_students)} sinh viên chưa có điểm thi kết thúc: {', '.join(missing_exam_students[:5])}",
                )

        now = datetime.now(timezone.utc)
        passed_count = 0
        failed_count = 0
        student_user_ids = []

        for enr in enrollments:
            uid = str(enr.get("userId"))
            if uid:
                student_user_ids.append(uid)

            task_scores = enr.get("taskScores", {})
            grades_data = enr.get("grades", {})
            exam_score = grades_data.get("examScore")

            if exam_score is None and exam_tasks:
                exam_scores_list = [task_scores[str(et.id)] for et in exam_tasks if str(et.id) in task_scores]
                if exam_scores_list:
                    exam_score = round(sum(exam_scores_list) / len(exam_scores_list), 2)
                elif force:
                    exam_score = 0.0
                else:
                    exam_score = None

            computed = grading_service.compute_student_grades(
                current_grades=grades_data,
                task_scores=task_scores,
                practice_task_ids=practice_ids,
                formula=course.grading_formula,
                exam_score_override=exam_score,
            )

            if computed.is_passed:
                passed_count += 1
            else:
                failed_count += 1

            # Cập nhật enrollment
            crud_enrollment.collection.update_one(
                {"_id": enr["_id"]},
                {
                    "$set": {
                        "grades": computed.model_dump(by_alias=True),
                        "isGradeLocked": True,
                        "updatedAt": now,
                    }
                },
            )

        # Cập nhật khóa học
        crud_course.collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "isGradeLocked": True,
                    "gradeLockedAt": now,
                    "gradeLockedBy": str(teacher_id),
                    "status": CourseStatus.COMPLETED.value,
                    "allowPracticeSubmission": False,
                    "allowExamSubmission": False,
                    "updatedAt": now,
                }
            },
        )

        # Gửi thông báo đến toàn bộ sinh viên trong lớp
        notification_service.notify_course_students(
            student_user_ids=student_user_ids,
            title=f"Chốt điểm môn học: {course.name}",
            message=f"Lớp học phần {course.name} đã chính thức chốt sổ điểm. Vui lòng kiểm tra bảng điểm cá nhân.",
            notif_type=NotificationType.GRADE_FINALIZED,
            link=f"/student/courses/{course_id}/grades",
        )

        return FinalizeGradesResponse(
            course_id=str(course_id),
            is_grade_locked=True,
            grade_locked_at=now,
            locked_by=str(teacher_id),
            total_students_graded=len(enrollments),
            passed_count=passed_count,
            failed_count=failed_count,
        )

    def unlock_grades(self, course_id: str, reason: str) -> UnlockGradesResponse:
        """Mở khóa sổ điểm lớp để điều chỉnh hoặc phúc khảo."""
        course = self.get_by_id(course_id)
        if not course.is_grade_locked:
            raise HTTPException(status_code=400, detail="Sổ điểm lớp học phần này hiện đang mở")

        now = datetime.now(timezone.utc)
        crud_course.collection.update_one(
            {"_id": ObjectId(course_id)},
            {
                "$set": {
                    "isGradeLocked": False,
                    "status": CourseStatus.IN_PROGRESS.value,
                    "updatedAt": now,
                }
            },
        )
        crud_enrollment.set_grade_lock_by_course(course_id, is_locked=False)

        return UnlockGradesResponse(
            course_id=str(course_id),
            is_grade_locked=False,
            unlocked_at=now,
        )

    def get_course_stats(self, course_id: str) -> CourseStatsResponse:
        """Thống kê kết quả học tập, phổ điểm A-F và tỷ lệ qua môn."""
        enrollments = list(crud_enrollment.collection.find({"courseId": str(course_id), "status": "active"}))
        total_students = len(enrollments)

        if total_students == 0:
            return CourseStatsResponse(
                course_id=str(course_id),
                total_students=0,
                pass_count=0,
                fail_count=0,
                pass_rate_percent=0.0,
                average_score=0.0,
                highest_score=0.0,
                lowest_score=0.0,
                grade_distribution=GradeDistribution(),
                submission_rate=0.0,
            )

        final_scores = []
        pass_count = 0
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        submitted_students = 0

        for enr in enrollments:
            if enr.get("taskScores"):
                submitted_students += 1

            grades = enr.get("grades", {})
            f_score = grades.get("finalScore")
            if f_score is not None:
                final_scores.append(f_score)
                letter = grades.get("letterGrade", "F")
                if "A" in letter:
                    distribution["A"] += 1
                elif "B" in letter:
                    distribution["B"] += 1
                elif "C" in letter:
                    distribution["C"] += 1
                elif "D" in letter:
                    distribution["D"] += 1
                else:
                    distribution["F"] += 1

                if grades.get("isPassed", False):
                    pass_count += 1

        fail_count = total_students - pass_count
        pass_rate = round((pass_count / total_students * 100.0), 1)
        avg_score = round(sum(final_scores) / len(final_scores), 2) if final_scores else 0.0
        hi_score = max(final_scores) if final_scores else 0.0
        lo_score = min(final_scores) if final_scores else 0.0
        sub_rate = round((submitted_students / total_students * 100.0), 1)

        return CourseStatsResponse(
            course_id=str(course_id),
            total_students=total_students,
            pass_count=pass_count,
            fail_count=fail_count,
            pass_rate_percent=pass_rate,
            average_score=avg_score,
            highest_score=hi_score,
            lowest_score=lo_score,
            grade_distribution=GradeDistribution(
                a=distribution["A"],
                b=distribution["B"],
                c=distribution["C"],
                d=distribution["D"],
                f=distribution["F"],
            ),
            submission_rate=sub_rate,
        )


course_service = CourseService()
