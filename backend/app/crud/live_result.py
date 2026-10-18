from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from pymongo import ReturnDocument

from app.crud.base import CRUDBase, to_object_id
from app.models.live_result import LiveResult
from app.schemas.live_result import LiveResultCreate, LiveResultUpdate


class CRUDLiveResult(CRUDBase[LiveResult, LiveResultCreate, LiveResultUpdate]):
    def get_by_task_and_user(
        self,
        task_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[LiveResult], int]:
        """Lấy danh sách kết quả thi trực tiếp của user cho một task."""
        return self.get_multi(
            filter={"taskId": str(task_id), "userId": str(user_id)},
            skip=skip,
            limit=limit,
            sort=[("startedAt", -1)],
        )

    def get_by_camera(
        self,
        camera_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[LiveResult], int]:
        """Lấy danh sách lượt thi được ghi nhận bởi camera."""
        return self.get_multi(
            filter={"cameraId": str(camera_id)},
            skip=skip,
            limit=limit,
            sort=[("startedAt", -1)],
        )

    def get_active_session(self, camera_id: str) -> Optional[LiveResult]:
        """Tìm phiên thi đang diễn ra tại camera (completedAt is null)."""
        doc = self.collection.find_one(
            {"cameraId": str(camera_id), "completedAt": None},
            sort=[("startedAt", -1)],
        )
        if not doc:
            return None
        return self.model.model_validate(doc)

    def finish_session(
        self,
        result_id: str | ObjectId,
        score: Optional[float] = None,
        metrics: Optional[dict[str, Any]] = None,
    ) -> Optional[LiveResult]:
        """Đánh dấu kết thúc phiên thi trực tiếp và lưu điểm số cuối cùng."""
        oid = to_object_id(result_id)
        if oid is None:
            return None

        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "completedAt": now,
            "updatedAt": now,
        }
        if score is not None:
            payload["score"] = score
        if metrics is not None:
            payload["metrics"] = metrics

        updated_doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_doc:
            return None
        return self.model.model_validate(updated_doc)


crud_live_result = CRUDLiveResult(LiveResult)
