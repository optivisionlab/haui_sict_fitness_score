import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.services.ai_grading_client import AIGradingError, ai_grading_client
from app.services.kafka_producer import kafka_producer

logger = logging.getLogger(__name__)

# Số lần gọi AI tối đa cho lỗi tạm thời (timeout, 5xx) trước khi báo failed
AI_MAX_ATTEMPTS = 3


class AIGradingWorker:
    def __init__(self):
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not getattr(settings, "AI_WORKER_ENABLED", True) or (self._task and not self._task.done()):
            return

        try:
            self._consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_GRADING_JOBS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP_AI,
                value_deserializer=lambda value: json.loads(value.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                # Một job có thể chờ AI tới AI_MAX_ATTEMPTS lần timeout; nếu vượt max_poll_interval
                # Kafka sẽ rebalance và giao lại job -> chấm trùng
                max_poll_interval_ms=int(
                    (settings.AI_API_TIMEOUT_SECONDS * AI_MAX_ATTEMPTS + 2 ** AI_MAX_ATTEMPTS + 60) * 1000
                ),
            )
            await self._consumer.start()
            self._running = True
            self._task = asyncio.create_task(self._consume())
            mode_desc = "MOCK mode" if settings.AI_MOCK_MODE else "REAL HTTP Client mode"
            logger.info("AI Grading Worker started in %s (group: %s)", mode_desc, settings.KAFKA_CONSUMER_GROUP_AI)
        except Exception as exc:
            self._running = False
            logger.warning("Could not start AI Grading Worker: %s", exc)

    @property
    def is_running(self) -> bool:
        return self._running

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception as e:
                logger.warning("Error stopping AI worker consumer: %s", e)
            self._consumer = None

    async def _consume(self) -> None:
        assert self._consumer is not None
        async for message in self._consumer:
            if not self._running:
                break

            job = message.value
            result_id = job.get("resultId") or job.get("jobId")
            logger.info("🤖 AI Worker: Processing grading job for resultId=%s", result_id)
            result = None
            error_code = "ai_api_error"
            for attempt in range(1, AI_MAX_ATTEMPTS + 1):
                try:
                    result = await ai_grading_client.grade(job)
                    logger.info("✅ AI Worker: Received response for resultId=%s (status=%s)", result_id, result.get("status"))
                    break
                except AIGradingError as exc:
                    error_code = exc.code
                    logger.warning("AI worker attempt %s failed for resultId=%s: %s", attempt, result_id, exc.code)
                    if not exc.retryable:
                        break
                except Exception:
                    logger.exception("AI worker request failed for resultId=%s", result_id)
                    break
                if attempt < AI_MAX_ATTEMPTS:
                    await asyncio.sleep(2 ** attempt)

            if result is None:
                result = {
                    "jobId": job.get("jobId"),
                    "resultId": result_id,
                    "status": "failed",
                    "errorCode": error_code,
                }

            if await kafka_producer.publish_grading_result(result):
                await self._consumer.commit()
            else:
                logger.error("Could not publish AI result; keeping Kafka job uncommitted")
                await asyncio.sleep(1)


# Giữ cả alias cũ AIMockWorker để tương thích ngược
AIMockWorker = AIGradingWorker
ai_grading_worker = AIGradingWorker()
ai_mock_worker = ai_grading_worker