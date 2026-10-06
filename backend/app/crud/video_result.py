from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.crud.base import CRUDBase, to_object_id
from app.models.video_result import VideoResult
from app.schemas.video_result import (
    VideoResultAIUpdate,
    VideoResultCreate,
    VideoResultTeacherGrade,
)


class CRUDVideoResult(CRUDBase[VideoResult, VideoResultCreate, VideoResultAIUpdate]):
    def get_by_task_and_user(
        self,
        task_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[VideoResult], int]:
        """Lấy tất cả các lần nộp bài của một sinh viên cho bài tập cụ thể, sắp xếp theo lần nộp mới nhất."""
        return self.get_multi(
            filter={"taskId": str(task_id), "userId": str(user_id)},
            skip=skip,
            limit=limit,
            sort=[("attemptNo", -1)],
        )

    def get_latest_attempt(self, task_id: str, user_id: str) -> Optional[VideoResult]:
        """Lấy lần nộp bài gần nhất."""
        doc = self.collection.find_one(
            {"taskId": str(task_id), "userId": str(user_id)},
            sort=[("attemptNo", -1)],
        )
        if not doc:
            return None
        return self.model.model_validate(doc)

    def get_next_attempt_number(self, task_id: str, user_id: str) -> int:
        """Tính số thứ tự lần nộp tiếp theo (1, 2, 3...)."""
        latest = self.get_latest_attempt(task_id, user_id)
        return (latest.attempt_no + 1) if latest else 1

    def get_pending(self, skip: int = 0, limit: int = 100) -> tuple[list[VideoResult], int]:
        """Lấy danh sách các video đang chờ AI xử lý (pending=true), ưu tiên video nộp trước."""
        return self.get_multi(
            filter={"pending": True},
            skip=skip,
            limit=limit,
            sort=[("submittedAt", 1)],
        )

    def update_ai_result(
        self,
        result_id: str | ObjectId,
        update_data: VideoResultAIUpdate | dict[str, Any],
    ) -> Optional[VideoResult]:
        """AI Worker cập nhật kết quả sau khi phân tích video xong."""
        oid = to_object_id(result_id)
        if oid is None:
            return None

        fields = (
            update_data.model_dump(by_alias=True, exclude_unset=True)
            if isinstance(update_data, BaseModel)
            else dict(update_data)
        )

        fields["pending"] = False
        fields["updatedAt"] = datetime.now(timezone.utc)

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def teacher_grade(
        self,
        result_id: str | ObjectId,
        grade_data: VideoResultTeacherGrade | dict[str, Any],
    ) -> Optional[VideoResult]:
        """Giáo viên chấm điểm thủ công (override điểm AI)."""
        oid = to_object_id(result_id)
        if oid is None:
            return None

        fields = (
            grade_data.model_dump(by_alias=True, exclude_unset=True)
            if isinstance(grade_data, BaseModel)
            else dict(grade_data)
        )

        now = datetime.now(timezone.utc)
        fields["gradedAt"] = now
        fields["updatedAt"] = now

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": fields},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)

    def get_best_score(self, task_id: str, user_id: str) -> Optional[float]:
        """Lấy điểm số cao nhất của sinh viên cho task (ưu tiên finalScore của GV nếu có, nếu không lấy aiScore)."""
        cursor = self.collection.find({
            "taskId": str(task_id),
            "userId": str(user_id),
            "pending": False,
        })
        scores = []
        for doc in cursor:
            score = doc.get("finalScore")
            if score is None:
                score = doc.get("aiScore")
            if score is not None:
                scores.append(float(score))
        return max(scores) if scores else None


crud_video_result = CRUDVideoResult(VideoResult)
