import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

from app.core.config import settings
from app.core.database import get_db
from app.services.minio_service import minio_service

logger = logging.getLogger(__name__)

# Chỉ object do upload-url sinh ra: submissions/{taskId}/{resultId}.{ext}
SUBMISSION_KEY_RE = re.compile(r"submissions/([0-9a-f]{24})/([0-9a-f]{24})\.[A-Za-z0-9]+")


class OrphanUploadCleaner:
    """
    Xóa video đã PUT lên MinIO nhưng không được confirm (không có video_results tương ứng).
    Không dùng lifecycle rule của MinIO vì rule không biết object nào đã có bài nộp.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.to_thread(self.cleanup_once)
            except Exception:
                logger.exception("Orphan upload cleanup failed")
            await asyncio.sleep(settings.UPLOAD_CLEANUP_INTERVAL_SEC)

    def cleanup_once(
        self,
        bucket: Optional[str] = None,
        max_age_sec: Optional[float] = None,
        now: Optional[datetime] = None,
    ) -> list[str]:
        bucket = bucket or minio_service.default_bucket
        max_age = settings.UPLOAD_ORPHAN_MAX_AGE_SEC if max_age_sec is None else max_age_sec
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(seconds=max_age)
        db = get_db()
        deleted: list[str] = []
        for obj in minio_service.client.list_objects(bucket, prefix="submissions/", recursive=True):
            match = SUBMISSION_KEY_RE.fullmatch(obj.object_name)
            if not match:
                continue
            if obj.last_modified is None or obj.last_modified > cutoff:
                continue
            task_id, result_id = ObjectId(match.group(1)), ObjectId(match.group(2))
            # An toàn: chỉ xóa khi task thuộc DB này, tránh xóa nhầm video thật khi app trỏ sai DB
            if not db.tasks.count_documents({"_id": task_id}, limit=1):
                continue
            if db.video_results.count_documents({"_id": result_id}, limit=1):
                continue
            if db.video_upload_sessions.count_documents({"resultId": result_id, "status": "uploading"}, limit=1):
                continue
            if minio_service.delete_file(obj.object_name, bucket):
                deleted.append(obj.object_name)
        if deleted:
            logger.info("Deleted %s orphan upload(s) from bucket %s", len(deleted), bucket)
        return deleted


orphan_upload_cleaner = OrphanUploadCleaner()
