from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from app.crud.base import CRUDBase, to_object_id
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate


class CRUDNotification(CRUDBase[Notification, NotificationCreate, dict]):
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        query: dict = {"userId": str(user_id)}
        if unread_only:
            query["isRead"] = False

        docs = self.collection.find(query).sort("createdAt", -1).limit(limit)
        return [self.model.model_validate(doc) for doc in docs]

    def mark_as_read(self, notification_id: str | ObjectId) -> Optional[Notification]:
        oid = to_object_id(notification_id)
        if not oid:
            return None
        doc = self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": {"isRead": True, "updatedAt": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return self.model.model_validate(doc) if doc else None

    def create_batch(self, notifications: list[dict]) -> int:
        if not notifications:
            return 0
        now = datetime.now(timezone.utc)
        for n in notifications:
            n.setdefault("createdAt", now)
            n.setdefault("updatedAt", now)
            n.setdefault("isRead", False)
        result = self.collection.insert_many(notifications)
        return len(result.inserted_ids)


crud_notification = CRUDNotification(Notification)
