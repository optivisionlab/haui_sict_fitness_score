import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener, TopicPartition
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_async_db
from app.services.ai_grading_client import AIGradingError, ai_grading_client
from app.services.grading_lanes import LANE_LARGE, LANE_SMALL, compute_ai_timeout
from app.services.kafka_producer import kafka_producer

logger = logging.getLogger(__name__)

COMMIT_INTERVAL_SEC = 2.0
TERMINAL_STATUSES = ("completed", "failed")

# Giới hạn số request đồng thời tới AI, dùng chung cho mọi pool trong process
_ai_semaphore: Optional[asyncio.Semaphore] = None


def get_ai_semaphore() -> asyncio.Semaphore:
    global _ai_semaphore
    if _ai_semaphore is None:
        _ai_semaphore = asyncio.Semaphore(settings.AI_MAX_CONCURRENCY)
    return _ai_semaphore


class OffsetTracker:
    """
    Theo dõi offset theo từng partition khi nhiều worker xử lý song song.
    Chỉ commit tới offset nhỏ nhất chưa xong: message phía sau đã xong nhưng message phía trước
    còn đang chạy thì chưa commit, để crash không làm mất message phía trước.
    """

    def __init__(self):
        self._pending: dict[TopicPartition, set[int]] = {}
        self._next: dict[TopicPartition, int] = {}
        self._committed: dict[TopicPartition, int] = {}

    def add(self, tp: TopicPartition, offset: int) -> None:
        self._pending.setdefault(tp, set()).add(offset)
        self._next[tp] = max(self._next.get(tp, 0), offset + 1)

    def done(self, tp: TopicPartition, offset: int) -> None:
        pending = self._pending.get(tp)
        if pending is not None:
            pending.discard(offset)

    def owns(self, tp: TopicPartition) -> bool:
        return tp in self._next

    def forget(self, tp: TopicPartition) -> None:
        self._pending.pop(tp, None)
        self._next.pop(tp, None)
        self._committed.pop(tp, None)

    def committable(self, partitions: Optional[set[TopicPartition]] = None) -> dict[TopicPartition, int]:
        """Offset cần commit (offset của message kế tiếp sẽ đọc), chỉ trả partition có thay đổi."""
        offsets: dict[TopicPartition, int] = {}
        for tp, next_offset in self._next.items():
            if partitions is not None and tp not in partitions:
                continue
            pending = self._pending.get(tp)
            offset = min(pending) if pending else next_offset
            if self._committed.get(tp) != offset:
                offsets[tp] = offset
        return offsets

    def mark_committed(self, offsets: dict[TopicPartition, int]) -> None:
        self._committed.update(offsets)

    def in_flight(self) -> int:
        return sum(len(p) for p in self._pending.values())


class _RebalanceListener(ConsumerRebalanceListener):
    def __init__(self, pool: "AIWorkerPool"):
        self._pool = pool

    async def on_partitions_revoked(self, revoked):
        await self._pool._on_revoked(set(revoked))

    async def on_partitions_assigned(self, assigned):
        logger.info("[%s] Partitions assigned: %s", self._pool.name, sorted(str(tp) for tp in assigned))


class AIWorkerPool:
    """
    1 consumer Kafka đọc job vào asyncio.Queue, N worker lấy job ra gọi AI.
    Worker rảnh thì lấy job tiếp theo, nên video dài không chặn video ngắn phía sau.
    """

    def __init__(
        self,
        name: str,
        topics: list[str],
        group_id: str,
        concurrency: int,
        timeout_fn: Optional[Callable[[dict[str, Any]], Optional[float]]] = None,
    ):
        self.name = name
        self.topics = topics
        self.group_id = group_id
        self.concurrency = max(1, concurrency)
        self.timeout_fn = timeout_fn
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._queue: Optional[asyncio.Queue] = None
        self._tracker = OffsetTracker()
        self._poll_task: Optional[asyncio.Task] = None
        self._commit_task: Optional[asyncio.Task] = None
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._paused = False
        self._busy = 0
        self._commit_lock = asyncio.Lock()
        self.stats = {"processed": 0, "failed": 0, "skipped_duplicate": 0}

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._consumer = AIOKafkaConsumer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=self.group_id,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        self._consumer.subscribe(self.topics, listener=_RebalanceListener(self))
        await self._consumer.start()
        self._queue = asyncio.Queue(maxsize=self.concurrency * 2)
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._commit_task = asyncio.create_task(self._commit_loop())
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(self.concurrency)]
        logger.info(
            "[%s] AI worker pool started: topics=%s group=%s concurrency=%s mock=%s",
            self.name, self.topics, self.group_id, self.concurrency, settings.AI_MOCK_MODE,
        )

    async def stop(self) -> None:
        if not self._running and self._consumer is None:
            return
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)

        # Job còn trong queue chưa chạy thì bỏ: offset của chúng vẫn pending nên không bị commit
        if self._queue:
            while not self._queue.empty():
                self._queue.get_nowait()
                self._queue.task_done()

        # Chờ job đang chạy trong thời gian grace, quá hạn thì hủy (sẽ được giao lại sau restart)
        if self._workers:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + settings.AI_WORKER_SHUTDOWN_GRACE
            if self._busy:
                logger.info("[%s] Draining %s running job(s), grace=%ss", self.name, self._busy, settings.AI_WORKER_SHUTDOWN_GRACE)
            while self._busy > 0 and loop.time() < deadline:
                await asyncio.sleep(0.2)
            if self._busy:
                logger.warning("[%s] Cancelling %s job(s) still running after grace period", self.name, self._busy)
            for task in self._workers:
                task.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers = []

        if self._commit_task:
            self._commit_task.cancel()
            await asyncio.gather(self._commit_task, return_exceptions=True)
        await self._commit()
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        logger.info("[%s] AI worker pool stopped: %s", self.name, self.stats)

    def health(self) -> dict[str, Any]:
        assignment = self._consumer.assignment() if self._consumer else set()
        return {
            "running": self._running,
            "topics": self.topics,
            "concurrency": self.concurrency,
            "queue_size": self._queue.qsize() if self._queue else 0,
            "paused": self._paused,
            "partitions": sorted(f"{tp.topic}-{tp.partition}" for tp in assignment),
            "in_flight": self._busy,
            **self.stats,
        }

    async def _poll_loop(self) -> None:
        assert self._consumer is not None and self._queue is not None
        while self._running:
            try:
                free = self._queue.maxsize - self._queue.qsize()
                if free <= 0:
                    self._set_paused(True)
                    await asyncio.sleep(0.2)
                    continue
                self._set_paused(False)
                batches = await self._consumer.getmany(timeout_ms=500, max_records=free)
                for tp, messages in batches.items():
                    for message in messages:
                        self._tracker.add(tp, message.offset)
                        await self._queue.put((tp, message))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[%s] Poll loop error, retrying in 1s", self.name)
                await asyncio.sleep(1)

    def _set_paused(self, paused: bool) -> None:
        if paused == self._paused or self._consumer is None:
            return
        partitions = self._consumer.assignment()
        if paused:
            self._consumer.pause(*partitions)
        else:
            self._consumer.resume(*partitions)
        self._paused = paused

    async def _commit_loop(self) -> None:
        while True:
            await asyncio.sleep(COMMIT_INTERVAL_SEC)
            await self._commit()

    async def _commit(self, partitions: Optional[set[TopicPartition]] = None) -> None:
        if self._consumer is None:
            return
        async with self._commit_lock:
            offsets = self._tracker.committable(partitions)
            assigned = self._consumer.assignment()
            offsets = {tp: off for tp, off in offsets.items() if tp in assigned}
            if not offsets:
                return
            try:
                await self._consumer.commit(offsets)
                self._tracker.mark_committed(offsets)
            except Exception as exc:
                logger.warning("[%s] Commit failed (sẽ thử lại): %s", self.name, exc)

    async def _on_revoked(self, revoked: set[TopicPartition]) -> None:
        await self._commit(revoked)
        for tp in revoked:
            self._tracker.forget(tp)
        logger.info("[%s] Partitions revoked: %s", self.name, sorted(str(tp) for tp in revoked))

    async def _worker(self, index: int) -> None:
        assert self._queue is not None
        while True:
            tp, message = await self._queue.get()
            try:
                if not self._tracker.owns(tp):
                    continue  # partition đã bị thu hồi, consumer mới sẽ xử lý message này
                self._busy += 1
                try:
                    if await self._handle(message.value):
                        self._tracker.done(tp, message.offset)
                finally:
                    self._busy -= 1
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[%s] Worker %s crashed on offset %s", self.name, index, message.offset)
            finally:
                self._queue.task_done()

    async def _is_already_graded(self, result_id: Optional[str]) -> bool:
        if not result_id or not ObjectId.is_valid(str(result_id)):
            return False
        doc = await get_async_db().video_results.find_one({"_id": ObjectId(str(result_id))}, {"status": 1})
        return bool(doc and doc.get("status") in TERMINAL_STATUSES)

    async def _handle(self, job: dict[str, Any]) -> bool:
        """Xử lý 1 job. Trả True khi đã xong (được phép commit offset)."""
        result_id = job.get("resultId") or job.get("jobId")
        if await self._is_already_graded(result_id):
            self.stats["skipped_duplicate"] += 1
            logger.info("[%s] Skip duplicate job resultId=%s (already graded)", self.name, result_id)
            return True

        timeout = self.timeout_fn(job) if self.timeout_fn else None
        started = time.monotonic()
        result = None
        error_code = "ai_api_error"
        attempt = 0
        busy_waited = 0.0
        while attempt < settings.AI_MAX_RETRIES:
            attempt += 1
            try:
                async with get_ai_semaphore():
                    result = await ai_grading_client.grade(job, timeout=timeout)
                break
            except AIGradingError as exc:
                error_code = exc.code
                if exc.busy and busy_waited < settings.AI_BUSY_MAX_WAIT_SEC and self._running:
                    # AI đang bận (429/503 + Retry-After): chờ theo AI yêu cầu, không tính vào AI_MAX_RETRIES
                    attempt -= 1
                    wait = min(exc.retry_after, settings.AI_BUSY_MAX_WAIT_SEC - busy_waited)
                    busy_waited += wait
                    logger.info("[%s] AI busy for resultId=%s, retrying in %.0fs", self.name, result_id, wait)
                    await asyncio.sleep(wait)
                    continue
                logger.warning("[%s] AI attempt %s failed for resultId=%s: %s", self.name, attempt, result_id, exc.code)
                if not exc.retryable:
                    break
            except Exception:
                logger.exception("[%s] AI request failed for resultId=%s", self.name, result_id)
                break
            if attempt < settings.AI_MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)

        if result is None:
            result = {"jobId": job.get("jobId"), "resultId": result_id, "status": "failed", "errorCode": error_code}
            self.stats["failed"] += 1
        else:
            self.stats["processed"] += 1
        logger.info(
            "[%s] Graded resultId=%s status=%s attempt=%s timeout=%s elapsed=%.1fs errorCode=%s",
            self.name, result_id, result.get("status"), attempt, timeout,
            time.monotonic() - started, result.get("errorCode"),
        )

        # Đã có kết quả: retry publish thay vì gọi lại AI. Đang tắt mà chưa publish được thì
        # để offset pending, job sẽ được giao lại sau restart.
        delay = 1.0
        while True:
            if await kafka_producer.publish_grading_result(result):
                return True
            if not self._running:
                logger.error("[%s] Could not publish result for resultId=%s before shutdown", self.name, result_id)
                return False
            logger.error("[%s] Could not publish result for resultId=%s, retrying in %.0fs", self.name, result_id, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)


def build_default_pools() -> list[AIWorkerPool]:
    """
    2 làn: small (video ngắn, thiếu durationSec) và large (video dài).
    Pool small giữ group cũ và đọc thêm topic cũ để consume nốt job tồn đọng (chuyển đổi topic).
    """
    return [
        AIWorkerPool(
            name=LANE_SMALL,
            topics=[settings.KAFKA_TOPIC_GRADING_JOBS_SMALL, settings.KAFKA_TOPIC_GRADING_JOBS],
            group_id=settings.KAFKA_CONSUMER_GROUP_AI,
            concurrency=settings.AI_POOL_SMALL_CONCURRENCY,
            timeout_fn=compute_ai_timeout,
        ),
        AIWorkerPool(
            name=LANE_LARGE,
            topics=[settings.KAFKA_TOPIC_GRADING_JOBS_LARGE],
            group_id=f"{settings.KAFKA_CONSUMER_GROUP_AI}-large",
            concurrency=settings.AI_POOL_LARGE_CONCURRENCY,
            timeout_fn=compute_ai_timeout,
        ),
    ]
