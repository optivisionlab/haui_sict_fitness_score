import asyncio
from confluent_kafka import KafkaException
from confluent_kafka.aio import AIOConsumer
from loguru import logger


class KafkaFrameConsumer:
    def __init__(
        self,
        consumer_conf,
        topic,
        group_id,
        *,
        max_pending_messages: int = 1,
        worker_concurrency: int = 1,
        poll_timeout: float = 1.0,
        drop_oldest_on_full: bool = True,
    ):
        self.topic = topic
        self.group_id = group_id
        self.max_pending_messages = max(1, int(max_pending_messages))
        self.worker_concurrency = max(1, int(worker_concurrency))
        self.poll_timeout = float(poll_timeout)
        self.drop_oldest_on_full = bool(drop_oldest_on_full)
        self.consumer = AIOConsumer({
            **consumer_conf,
            "group.id": group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
        })
        self.running = False

    async def _worker_loop(self, queue: asyncio.Queue, handle_message):
        while True:
            msg = await queue.get()
            try:
                if msg is None:
                    return

                await handle_message(msg)
                await self.consumer.store_offsets(message=msg)
                await self.consumer.commit(asynchronous=True)
            except Exception:
                logger.exception(f"[{self.group_id}] Error while processing message")
            finally:
                queue.task_done()

    async def start(self, handle_message):
        await self.consumer.subscribe([self.topic])
        self.running = True
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_pending_messages)
        workers = [
            asyncio.create_task(self._worker_loop(queue, handle_message))
            for _ in range(self.worker_concurrency)
        ]
        logger.info(
            f"[{self.group_id}] Subscribed to {self.topic} "
            f"(max_pending_messages={self.max_pending_messages}, worker_concurrency={self.worker_concurrency})"
        )

        try:
            while self.running:
                msg = await self.consumer.poll(self.poll_timeout)
                if msg is None:
                    continue
                if msg.error():
                    raise KafkaException(msg.error())

                if queue.full() and self.drop_oldest_on_full:
                    dropped = queue.get_nowait()
                    queue.task_done()
                    logger.debug(
                        f"[{self.group_id}] Dropped stale frame offset={dropped.offset()} on topic={dropped.topic()}"
                    )

                await queue.put(msg)
        finally:
            self.running = False
            await queue.join()
            for _ in workers:
                await queue.put(None)
            await asyncio.gather(*workers, return_exceptions=True)
            await self.consumer.close()

    def stop(self):
        self.running = False