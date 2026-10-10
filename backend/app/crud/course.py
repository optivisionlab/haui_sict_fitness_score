from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.crud.base import CRUDBase, to_object_id
from app.models.course import Course, Week
from app.schemas.course import CourseCreate, CourseUpdate, WeekCreate, WeekUpdate


class CRUDCourse(CRUDBase[Course, CourseCreate, CourseUpdate]):
    def get_by_key(self, key: str) -> Optional[Course]:
        """Tìm khóa học theo key (slug)."""
        doc = self.collection.find_one({"key": key.strip()})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_by_code(self, code: str) -> Optional[Course]:
        """Tìm khóa học theo mã môn học."""
        doc = self.collection.find_one({"code": code.strip()})
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_by_teacher(
        self,
        teacher_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Course], int]:
        """Lấy danh sách khóa học do một giáo viên giảng dạy."""
        return self.get_multi(filter={"teacherId": str(teacher_id)}, skip=skip, limit=limit)

    def add_week(
        self,
        course_id: str | ObjectId,
        week: Week | WeekCreate | dict[str, Any],
    ) -> Optional[Course]:
        """Thêm 1 tuần học vào danh sách weeks của khóa học."""
        oid = to_object_id(course_id)
        if oid is None:
            return None

        week_doc = week.model_dump(by_alias=True) if isinstance(week, BaseModel) else dict(week)

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {
                "$push": {"weeks": week_doc},
                "$set": {"updatedAt": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def update_week(
        self,
        course_id: str | ObjectId,
        week_order: int,
        week: Week | WeekUpdate | dict[str, Any],
    ) -> Optional[Course]:
        """Cập nhật thông tin của một tuần học theo order."""
        oid = to_object_id(course_id)
        if oid is None:
            return None

        update_fields = (
            week.model_dump(by_alias=True, exclude_unset=True)
            if isinstance(week, BaseModel)
            else dict(week)
        )

        set_payload = {f"weeks.$.{k}": v for k, v in update_fields.items()}
        set_payload["updatedAt"] = datetime.now(timezone.utc)

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid, "weeks.order": week_order},
            {"$set": set_payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def delete_week(
        self,
        course_id: str | ObjectId,
        week_order: int,
    ) -> Optional[Course]:
        """Xóa một tuần học khỏi khóa học."""
        oid = to_object_id(course_id)
        if oid is None:
            return None

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {
                "$pull": {"weeks": {"order": week_order}},
                "$set": {"updatedAt": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def increment_student_total(
        self,
        course_id: str | ObjectId,
        amount: int = 1,
    ) -> Optional[Course]:
        """Tăng hoặc giảm tổng số sinh viên đăng ký khóa học."""
        oid = to_object_id(course_id)
        if oid is None:
            return None

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {
                "$inc": {"studentTotal": amount},
                "$set": {"updatedAt": datetime.now(timezone.utc)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)


crud_course = CRUDCourse(Course)
