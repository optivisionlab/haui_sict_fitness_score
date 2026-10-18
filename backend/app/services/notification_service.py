from typing import Optional

from app.crud.notification import crud_notification
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationCreate


class NotificationService:
    def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notif_type: NotificationType = NotificationType.GENERAL,
        link: Optional[str] = None,
    ) -> Notification:
        data = NotificationCreate(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            link=link,
        )
        return crud_notification.create(data)

    def notify_course_students(
        self,
        student_user_ids: list[str],
        title: str,
        message: str,
        notif_type: NotificationType = NotificationType.GENERAL,
        link: Optional[str] = None,
    ) -> int:
        if not student_user_ids:
            return 0
        batch = [
            {
                "userId": uid,
                "type": notif_type.value,
                "title": title,
                "message": message,
                "link": link,
            }
            for uid in student_user_ids
        ]
        return crud_notification.create_batch(batch)

    def get_user_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50
    ) -> list[Notification]:
        return crud_notification.get_user_notifications(
            user_id=user_id, unread_only=unread_only, limit=limit
        )

    def mark_read(self, notification_id: str) -> Optional[Notification]:
        return crud_notification.mark_as_read(notification_id)

    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        notification = crud_notification.get(notification_id)
        if not notification:
            return False
        if str(notification.user_id) != str(user_id):
            return False
        return crud_notification.delete(notification_id)


notification_service = NotificationService()
