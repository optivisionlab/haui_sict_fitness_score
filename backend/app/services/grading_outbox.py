import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.core.database import get_async_db
from app.services.grading_lanes import job_duration_sec, lane_topic, resolve_lane
from app.services.kafka_producer import kafka_producer

logger = logging.getLogger(__name__)

OUTBOX_BATCH_SIZE = 20
OUTBOX_MAX_ATTEMPTS = 10
OUTBOX_LEASE_SECONDS = 900


class GradingOutboxDispatcher:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        # Job chấm theo direct fallback đang chạy (mỗi job 1 task, không chặn vòng lặp poll)
        self._fallback_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._fallback_tasks:
            from app.core.config import settings

            logger.info("Waiting for %s direct-fallback job(s)", len(self._fallback_tasks))
            _, still_running = await asyncio.wait(self._fallback_tasks, timeout=settings.AI_WORKER_SHUTDOWN_GRACE)
            for task in still_running:
                task.cancel()
            if still_running:
                logger.warning("Cancelled %s direct-fallback job(s) after grace period", len(still_running))
                await asyncio.gather(*still_running, return_exceptions=True)

    async def _run(self) -> None:
        while self._running:
            try:
                await self.dispatch_pending()
            except Exception:
                logger.exception("Grading outbox dispatch cycle failed")
            await asyncio.sleep(1)

    async def dispatch_pending(self) -> int:
        if not kafka_producer.is_ready:
            from app.core.config import settings
            if settings.AI_DIRECT_FALLBACK:
                return await self._dispatch_direct_fallback()
            return 0

        collection = get_async_db().video_results
        dispatched = 0
        for _ in range(OUTBOX_BATCH_SIZE):
            now = datetime.now(timezone.utc)
            document = await collection.find_one_and_update(
                {
                    "gradingJob": {"$exists": True},
                    "$or": [
                        {
                            "gradingJobStatus": "pending",
                            "$or": [
                                {"gradingJobNextAttemptAt": {"$exists": False}},
                                {"gradingJobNextAttemptAt": {"$lte": now}},
                            ],
                        },
                        {
                            "gradingJobStatus": "processing",
                            "gradingJobLeaseUntil": {"$lte": now},
                        },
                    ],
                },
                {
                    "$set": {
                        "gradingJobStatus": "processing",
                        "gradingJobLeaseUntil": now + timedelta(seconds=OUTBOX_LEASE_SECONDS),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if not document:
                break

            job = document["gradingJob"]
            duration = job_duration_sec(job, fallback=document.get("durationSec"))
            lane = resolve_lane(duration)
            if duration is not None and job.get("durationSec") is None:
                job = {**job, "durationSec": duration}
            if job.get("fileSize") is None and document.get("fileSize") is not None:
                job = {**job, "fileSize": document["fileSize"]}
            if await kafka_producer.publish_grading_job(job, topic=lane_topic(lane)):
                await collection.update_one(
                    {"_id": document["_id"], "gradingJobStatus": "processing"},
                    {
                        "$set": {
                            "gradingJobStatus": "sent",
                            "gradingJobSentAt": datetime.now(timezone.utc),
                            "gradingJobLane": lane,
                        },
                        "$unset": {"gradingJobLeaseUntil": "", "gradingJobNextAttemptAt": ""},
                    },
                )
                dispatched += 1
                continue

            attempts = int(document.get("gradingJobAttempts", 0)) + 1
            update = {
                "$set": {
                    "gradingJobStatus": "failed" if attempts >= OUTBOX_MAX_ATTEMPTS else "pending",
                    "gradingJobAttempts": attempts,
                },
                "$unset": {"gradingJobLeaseUntil": ""},
            }
            if attempts >= OUTBOX_MAX_ATTEMPTS:
                update["$set"].update({"status": "failed", "pending": False, "error": "kafka_publish_failed"})
                logger.error("Grading job exhausted retries: resultId=%s", job.get("resultId"))
            else:
                delay = min(2 ** attempts, 60)
                update["$set"]["gradingJobNextAttemptAt"] = datetime.now(timezone.utc) + timedelta(seconds=delay)
            await collection.update_one(
                {"_id": document["_id"], "gradingJobStatus": "processing"},
                update,
            )

        return dispatched

    async def _dispatch_direct_fallback(self) -> int:
        """
        Fallback: Kafka chưa sẵn sàng thì gọi thẳng AI. Mỗi job chạy trong 1 task riêng, dùng chung
        semaphore AI_MAX_CONCURRENCY với worker pool, nên vòng lặp outbox không bị chặn tới khi AI trả về.
        Chỉ claim thêm job khi còn slot để job đã claim không phải nằm chờ semaphore.
        """
        from app.core.config import settings

        collection = get_async_db().video_results
        started = 0
        lease = max(OUTBOX_LEASE_SECONDS, settings.AI_TIMEOUT_MAX_SEC + 60)
        while self._running and len(self._fallback_tasks) < settings.AI_MAX_CONCURRENCY:
            now = datetime.now(timezone.utc)
            document = await collection.find_one_and_update(
                {
                    "gradingJob": {"$exists": True},
                    "$or": [
                        {
                            "gradingJobStatus": "pending",
                            "$or": [
                                {"gradingJobNextAttemptAt": {"$exists": False}},
                                {"gradingJobNextAttemptAt": {"$lte": now}},
                            ],
                        },
                        {
                            "gradingJobStatus": "processing",
                            "gradingJobLeaseUntil": {"$lte": now},
                        },
                    ],
                },
                {
                    "$set": {
                        "gradingJobStatus": "processing",
                        "gradingJobLeaseUntil": now + timedelta(seconds=lease),
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            if not document:
                break
            task = asyncio.create_task(self._grade_direct(document))
            self._fallback_tasks.add(task)
            task.add_done_callback(self._fallback_tasks.discard)
            started += 1
        return started

    async def _grade_direct(self, document: dict) -> None:
        from app.schemas.video_result import VideoResultAIUpdate
        from app.services.ai_grading_client import AIGradingError, ai_grading_client
        from app.services.ai_worker_pool import get_ai_semaphore
        from app.services.grading_lanes import compute_ai_timeout
        from app.services.video_result_service import video_result_service

        collection = get_async_db().video_results
        job = document["gradingJob"]
        for field in ("durationSec", "fileSize"):
            if job.get(field) is None and document.get(field) is not None:
                job = {**job, field: document[field]}
        result_id = str(document["_id"])
        try:
            async with get_ai_semaphore():
                ai_res = await ai_grading_client.grade(job, timeout=compute_ai_timeout(job))
            ai_update = VideoResultAIUpdate(
                pending=False,
                metrics=ai_res.get("metrics", {}),
                ai_score=ai_res.get("aiScore"),
                ai_comment=ai_res.get("aiComment"),
            )
            await asyncio.to_thread(video_result_service.ai_callback, result_id, ai_update)
            await collection.update_one(
                {"_id": document["_id"]},
                {
                    "$set": {
                        "gradingJobStatus": "completed",
                        "gradingJobSentAt": datetime.now(timezone.utc),
                    },
                    "$unset": {"gradingJobLeaseUntil": "", "gradingJobNextAttemptAt": ""},
                },
            )
        except asyncio.CancelledError:
            # Bị hủy khi tắt app: trả job về pending ngay, không bắt chờ hết lease mới được chấm lại
            await collection.update_one(
                {"_id": document["_id"], "gradingJobStatus": "processing"},
                {"$set": {"gradingJobStatus": "pending"}, "$unset": {"gradingJobLeaseUntil": ""}},
            )
            raise
        except Exception as exc:
            logger.warning("Direct grading fallback attempt failed for resultId=%s: %s", result_id, exc)
            busy = isinstance(exc, AIGradingError) and exc.busy
            # AI đang bận thì không tính là một lần thất bại
            attempts = int(document.get("gradingJobAttempts", 0)) + (0 if busy else 1)
            # Lỗi vĩnh viễn (request/video không hợp lệ) thì không retry
            terminal = attempts >= OUTBOX_MAX_ATTEMPTS or (
                isinstance(exc, AIGradingError) and not exc.retryable
            )
            error_code = exc.code if isinstance(exc, AIGradingError) else "ai_grading_failed"
            update = {
                "$set": {
                    "gradingJobStatus": "failed" if terminal else "pending",
                    "gradingJobAttempts": attempts,
                },
                "$unset": {"gradingJobLeaseUntil": ""},
            }
            if terminal:
                update["$set"].update({"status": "failed", "pending": False, "error": error_code})
            else:
                delay = exc.retry_after if busy else min(2 ** attempts, 60)
                update["$set"]["gradingJobNextAttemptAt"] = datetime.now(timezone.utc) + timedelta(seconds=delay)
            await collection.update_one({"_id": document["_id"]}, update)

grading_outbox_dispatcher = GradingOutboxDispatcher()