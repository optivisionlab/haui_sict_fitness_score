import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.core.database import get_db
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

        collection = get_db().video_results
        dispatched = 0
        for _ in range(OUTBOX_BATCH_SIZE):
            now = datetime.now(timezone.utc)
            document = await asyncio.to_thread(
                collection.find_one_and_update,
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
            if await kafka_producer.publish_grading_job(job, topic=lane_topic(lane)):
                await asyncio.to_thread(
                    collection.update_one,
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
            await asyncio.to_thread(
                collection.update_one,
                {"_id": document["_id"], "gradingJobStatus": "processing"},
                update,
            )

        return dispatched

    async def _dispatch_direct_fallback(self) -> int:
        """Fallback: Nếu Kafka broker chưa chạy, trực tiếp gọi AI client để chấm điểm bài nộp."""
        from app.services.ai_grading_client import AIGradingError, ai_grading_client
        from app.services.video_result_service import video_result_service
        from app.schemas.video_result import VideoResultAIUpdate

        collection = get_db().video_results
        dispatched = 0
        now = datetime.now(timezone.utc)
        for _ in range(OUTBOX_BATCH_SIZE):
            document = await asyncio.to_thread(
                collection.find_one_and_update,
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
            result_id = str(document["_id"])
            try:
                ai_res = await ai_grading_client.grade(job)
                ai_update = VideoResultAIUpdate(
                    pending=False,
                    metrics=ai_res.get("metrics", {}),
                    ai_score=ai_res.get("aiScore"),
                    ai_comment=ai_res.get("aiComment"),
                )
                await asyncio.to_thread(video_result_service.ai_callback, result_id, ai_update)
                await asyncio.to_thread(
                    collection.update_one,
                    {"_id": document["_id"]},
                    {
                        "$set": {
                            "gradingJobStatus": "completed",
                            "gradingJobSentAt": datetime.now(timezone.utc),
                        },
                        "$unset": {"gradingJobLeaseUntil": "", "gradingJobNextAttemptAt": ""},
                    },
                )
                dispatched += 1
            except Exception as exc:
                logger.warning("Direct grading fallback attempt failed for resultId=%s: %s", result_id, exc)
                attempts = int(document.get("gradingJobAttempts", 0)) + 1
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
                    delay = min(2 ** attempts, 60)
                    update["$set"]["gradingJobNextAttemptAt"] = datetime.now(timezone.utc) + timedelta(seconds=delay)
                await asyncio.to_thread(collection.update_one, {"_id": document["_id"]}, update)

        return dispatched


grading_outbox_dispatcher = GradingOutboxDispatcher()