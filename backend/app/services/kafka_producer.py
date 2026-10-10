import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from aiokafka import AIOKafkaProducer
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self):
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_ready: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self):
        """Khởi động Kafka Producer kết nối tới broker."""
        try:
            self._loop = asyncio.get_running_loop()
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            await self._producer.start()
            self._is_ready = True
            logger.info("Kafka Producer started successfully -> %s", settings.KAFKA_BOOTSTRAP_SERVERS)
        except Exception as e:
            self._is_ready = False
            logger.error("Failed to start Kafka Producer: %s", e)

    async def stop(self):
        """Dừng Kafka Producer an toàn."""
        if self._producer:
            try:
                await self._producer.stop()
                self._is_ready = False
                logger.info("Kafka Producer stopped")
            except Exception as e:
                logger.warning("Error stopping Kafka Producer: %s", e)

    async def send_grading_job(
        self,
        result_id: str,
        task_id: str,
        sport_id: str,
        sport_code: str,
        user_id: str,
        video_url: str,
        attempt_no: int = 1,
        priority: str = "normal",
    ) -> bool:
        """
        Gửi job chấm điểm video vào Kafka topic `video-grading-jobs`.
        Trả về True nếu gửi thành công, False nếu thất bại.
        """
        if not self._producer or not self._is_ready:
            logger.warning("Kafka Producer is not ready. Skipping message for resultId=%s", result_id)
            return False

        message: dict[str, Any] = {
            "jobId": result_id,
            "resultId": result_id,
            "taskId": task_id,
            "sportId": sport_id,
            "sportCode": sport_code,
            "userId": user_id,
            "videoUrl": video_url,
            "minioEndpoint": settings.MINIO_ENDPOINT,
            "minioBucket": settings.MINIO_BUCKET_NAME,
            "attemptNo": attempt_no,
            "priority": priority,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Gửi message với key=result_id để các message cùng bài nộp luôn vào 1 partition
            await self._producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_GRADING_JOBS,
                value=message,
                key=result_id,
            )
            logger.info("📤 Kafka Producer: Sent grading job -> resultId=%s, sport=%s", result_id, sport_code)
            return True
        except Exception as e:
            logger.exception("Kafka Producer error sending job for resultId=%s: %s", result_id, e)
            return False

    def dispatch_grading_job(
        self,
        result_id: str,
        task_id: str,
        sport_id: str,
        sport_code: str,
        user_id: str,
        video_url: str,
        attempt_no: int = 1,
        priority: str = "normal",
    ):
        """
        Thread-safe helper để dispatch coroutine gửi job vào Kafka từ bất kỳ thread nào
        (kể cả sync route handler của FastAPI).
        """
        if not self._producer or not self._is_ready:
            logger.warning("Kafka Producer is not ready, cannot dispatch job for resultId=%s", result_id)
            return

        coro = self.send_grading_job(
            result_id=result_id,
            task_id=task_id,
            sport_id=sport_id,
            sport_code=sport_code,
            user_id=user_id,
            video_url=video_url,
            attempt_no=attempt_no,
            priority=priority,
        )

        try:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, self._loop)
            else:
                try:
                    running_loop = asyncio.get_running_loop()
                    running_loop.create_task(coro)
                except RuntimeError:
                    asyncio.run(coro)
        except Exception as e:
            logger.error("Failed to schedule Kafka grading job dispatch: %s", e)


kafka_producer = KafkaProducerService()
