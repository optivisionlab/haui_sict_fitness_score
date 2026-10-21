import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer, TopicPartition
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.video_result import VideoResultAIUpdate

logger = logging.getLogger(__name__)

RESULT_RETRY_DELAY_SEC = 2


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
                enable_auto_commit=False,
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

    @property
    def is_running(self) -> bool:
        return self._is_running

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
        """
        Vòng lặp lắng nghe message kết quả từ Kafka.
        Commit thủ công từng message sau khi đã ghi MongoDB xong; lỗi tạm thời thì seek lại đúng
        offset để xử lý lại, nên không mất kết quả khi Mongo tạm lỗi hoặc app crash.
        """
        logger.info("Kafka Result Consumer loop is listening...")
        while self._is_running:
            try:
                assert self._consumer is not None
                async for msg in self._consumer:
                    tp = TopicPartition(msg.topic, msg.partition)
                    try:
                        await self._process(msg.value)
                    except HTTPException as exc:
                        # Lỗi nghiệp vụ vĩnh viễn (vd. resultId không tồn tại): bỏ qua message
                        logger.warning(
                            "Kafka Consumer: skip result offset=%s: %s %s", msg.offset, exc.status_code, exc.detail
                        )
                    except Exception:
                        logger.exception(
                            "Kafka Consumer: failed to store result offset=%s, retrying in %ss",
                            msg.offset,
                            RESULT_RETRY_DELAY_SEC,
                        )
                        self._consumer.seek(tp, msg.offset)
                        await asyncio.sleep(RESULT_RETRY_DELAY_SEC)
                        continue
                    await self._consumer.commit({tp: msg.offset + 1})
            except asyncio.CancelledError:
                break
            except Exception as loop_err:
                if not self._is_running:
                    break
                logger.error("Error in Kafka consume loop, reconnecting in 5s: %s", loop_err)
                await asyncio.sleep(5)

    async def _process(self, data: dict) -> None:
        from app.services.video_result_service import video_result_service

        result_id = data.get("resultId")
        status = data.get("status", "completed")
        logger.info("📥 Kafka Consumer: Received result for resultId=%s, status=%s", result_id, status)

        if not result_id:
            logger.warning("Kafka message missing resultId: %s", data)
            return

        if status == "completed":
            ai_update = VideoResultAIUpdate(
                pending=False,
                metrics=data.get("metrics", {}),
                ai_score=data.get("aiScore"),
                ai_comment=data.get("aiComment"),
            )
            await asyncio.to_thread(video_result_service.ai_callback, result_id, ai_update)
            logger.info("✅ Kafka Consumer: Successfully processed result for resultId=%s", result_id)
        elif status == "failed":
            error_code = str(data.get("errorCode") or "ai_processing_failed")[:100]
            await asyncio.to_thread(video_result_service.ai_failure, result_id, error_code)
            logger.warning(
                "Kafka Consumer: job failed for resultId=%s, code=%s",
                result_id,
                error_code,
            )

kafka_result_consumer = KafkaResultConsumerService()
