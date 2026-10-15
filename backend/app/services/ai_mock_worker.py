import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.services.ai_grading_client import ai_grading_client
from app.services.kafka_producer import kafka_producer

logger = logging.getLogger(__name__)


class AIMockWorker:
    def __init__(self):
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if not settings.AI_MOCK_MODE or (self._task and not self._task.done()):
            return

        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_GRADING_JOBS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP_AI,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._consume())
        logger.warning("AI mock worker started; disable real AI workers for this consumer group")

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
            await self._consumer.stop()
            self._consumer = None

    async def _consume(self) -> None:
        assert self._consumer is not None
        async for message in self._consumer:
            if not self._running:
                break

            job = message.value
            try:
                result = await ai_grading_client.grade(job)
            except Exception:
                logger.exception("AI mock worker request failed for resultId=%s", job.get("resultId"))
                result = {
                    "jobId": job.get("jobId"),
                    "resultId": job.get("resultId"),
                    "status": "failed",
                    "errorCode": "ai_api_error",
                }

            if await kafka_producer.publish_grading_result(result):
                await self._consumer.commit()
            else:
                logger.error("Could not publish AI result; keeping Kafka job uncommitted")
                await asyncio.sleep(1)


ai_mock_worker = AIMockWorker()