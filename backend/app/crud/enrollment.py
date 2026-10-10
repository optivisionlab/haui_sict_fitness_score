from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from pymongo import ReturnDocument

from app.crud.base import CRUDBase, to_object_id
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


class CRUDEnrollment(CRUDBase[Enrollment, EnrollmentCreate, EnrollmentUpdate]):
    def get_by_user_and_course(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        """Lấy bản ghi ghi danh của user trong một khóa học cụ thể."""
        doc = self.collection.find_one({
            "userId": str(user_id),
            "courseId": str(course_id),
        })
        if not doc:
            return None
        return self.model.model_validate(doc)

    def is_enrolled(self, user_id: str, course_id: str) -> bool:
        """Kiểm tra user đã đăng ký khóa học này hay chưa."""
        return self.collection.count_documents({
            "userId": str(user_id),
            "courseId": str(course_id),
        }, limit=1) > 0

    def get_by_user(
        self,
        user_id: str,
        status: Optional[EnrollmentStatus | str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Enrollment], int]:
        """Lấy danh sách khóa học mà sinh viên đã đăng ký."""
        query: dict = {"userId": str(user_id)}
        if status:
            query["status"] = status.value if isinstance(status, EnrollmentStatus) else str(status)
        return self.get_multi(filter=query, skip=skip, limit=limit)

    def get_by_course(
        self,
        course_id: str,
        status: Optional[EnrollmentStatus | str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Enrollment], int]:
        """Lấy danh sách sinh viên đăng ký một khóa học."""
        query: dict = {"courseId": str(course_id)}
        if status:
            query["status"] = status.value if isinstance(status, EnrollmentStatus) else str(status)
        return self.get_multi(filter=query, skip=skip, limit=limit)

    def record_task_completion(
        self,
        enrollment_id: str | ObjectId,
        task_id: str,
        score: float,
        progress_percent: Optional[float] = None,
    ) -> Optional[Enrollment]:
        """Ghi nhận hoàn thành 1 task, cập nhật task_scores và completed_task_ids."""
        oid = to_object_id(enrollment_id)
        if oid is None:
            return None

        set_payload: dict = {
            f"taskScores.{str(task_id)}": score,
            "updatedAt": datetime.now(timezone.utc),
        }
        if progress_percent is not None:
            set_payload["progressPercent"] = progress_percent
            if progress_percent >= 100.0:
                set_payload["status"] = EnrollmentStatus.DONE.value

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {
                "$addToSet": {"completedTaskIds": str(task_id)},
                "$set": set_payload,
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def update_progress(
        self,
        enrollment_id: str | ObjectId,
        progress_percent: float,
        status: Optional[EnrollmentStatus] = None,
    ) -> Optional[Enrollment]:
        """Cập nhật tiến độ học tập (%)."""
        oid = to_object_id(enrollment_id)
        if oid is None:
            return None

        payload: dict = {
            "progressPercent": progress_percent,
            "updatedAt": datetime.now(timezone.utc),
        }
        if status:
            payload["status"] = status.value
        elif progress_percent >= 100.0:
            payload["status"] = EnrollmentStatus.DONE.value

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def update_grades_data(
        self,
        enrollment_id: str | ObjectId,
        grades_dict: dict,
        note: Optional[str] = None,
    ) -> Optional[Enrollment]:
        """Cập nhật cấu trúc điểm grades cho một enrollment."""
        oid = to_object_id(enrollment_id)
        if oid is None:
            return None

        payload: dict = {
            "grades": grades_dict,
            "updatedAt": datetime.now(timezone.utc),
        }
        if note is not None:
            payload["note"] = note

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def set_grade_lock_by_course(self, course_id: str, is_locked: bool) -> int:
        """Đồng bộ cờ isGradeLocked cho toàn bộ sinh viên trong một khóa học."""
        result = self.collection.update_many(
            {"courseId": str(course_id)},
            {"$set": {"isGradeLocked": is_locked, "updatedAt": datetime.now(timezone.utc)}},
        )
        return result.modified_count


crud_enrollment = CRUDEnrollment(Enrollment)

