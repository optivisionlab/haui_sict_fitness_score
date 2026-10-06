import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.schemas.video_result import VideoResultAIUpdate

logger = logging.getLogger(__name__)


class KafkaResultConsumerService:
    def __init__(self):
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._consume_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    async def start(self):
        """Khởi động Kafka Consumer nhận kết quả từ AI Worker."""
        try:
            self._consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_GRADING_RESULTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP_BACKEND,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            await self._consumer.start()
            self._is_running = True
            self._consume_task = asyncio.create_task(self._consume_loop())
            logger.info(
                "Kafka Result Consumer started -> topic: %s, group: %s",
                settings.KAFKA_TOPIC_GRADING_RESULTS,
                settings.KAFKA_CONSUMER_GROUP_BACKEND,
            )
        except Exception as e:
            self._is_running = False
            logger.error("Failed to start Kafka Result Consumer: %s", e)

    async def stop(self):
        """Dừng Consumer an toàn."""
        self._is_running = False
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            try:
                await self._consumer.stop()
                logger.info("Kafka Result Consumer stopped")
            except Exception as e:
                logger.warning("Error stopping Kafka Consumer: %s", e)

    async def _consume_loop(self):
        """Vòng lặp lắng nghe message kết quả từ Kafka."""
        from app.services.video_result_service import video_result_service

        logger.info("Kafka Result Consumer loop is listening...")
        while self._is_running:
            try:
                assert self._consumer is not None
                async for msg in self._consumer:
                    try:
                        data = msg.value
                        result_id = data.get("resultId")
                        status = data.get("status", "completed")
                        logger.info("📥 Kafka Consumer: Received result for resultId=%s, status=%s", result_id, status)

                        if not result_id:
                            logger.warning("Kafka message missing resultId: %s", data)
                            continue

                        if status == "completed":
                            ai_update = VideoResultAIUpdate(
                                pending=False,
                                metrics=data.get("metrics", {}),
                                ai_score=data.get("aiScore"),
                                ai_comment=data.get("aiComment"),
                            )
                            video_result_service.ai_callback(result_id, ai_update)
                            logger.info("✅ Kafka Consumer: Successfully processed result for resultId=%s", result_id)
                        elif status == "failed":
                            logger.warning(
                                "❌ Kafka Consumer: Job marked as failed for resultId=%s, error=%s",
                                result_id,
                                data.get("error"),
                            )
                    except Exception as msg_err:
                        logger.exception("Error processing individual Kafka message: %s", msg_err)
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                if not self._is_running:
                    break
                logger.error("Error in Kafka consume loop, reconnecting in 5s: %s", loop_err)
                await asyncio.sleep(5)


kafka_result_consumer = KafkaResultConsumerService()
