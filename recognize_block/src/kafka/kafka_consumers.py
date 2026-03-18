import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

from confluent_kafka import KafkaException, TopicPartition
from confluent_kafka.aio import AIOConsumer
from loguru import logger


@dataclass
class _PartitionOffsetTracker:
    last_committed: Optional[int] = None
    done: Set[int] = field(default_factory=set)

    def ensure_initialized(self, first_seen_offset: int) -> None:
        if self.last_committed is None:
            self.last_committed = first_seen_offset - 1

    def mark_done(self, offset: int) -> None:
        self.done.add(int(offset))

    def highest_contiguous_done(self) -> Optional[int]:
        if self.last_committed is None:
            return None

        cur = self.last_committed
        while (cur + 1) in self.done:
            cur += 1

        if cur == self.last_committed:
            return None
        return cur

    def advance_after_commit(self, committed_through: int) -> None:
        start = self.last_committed + 1
        for off in range(start, committed_through + 1):
            self.done.discard(off)
        self.last_committed = committed_through


class KafkaFrameConsumer:
    def __init__(
        self,
        consumer_conf,
        topic,
        group_id,
        *,
        max_pending_messages: int = 32,
        worker_concurrency: int = 4,
        poll_timeout: float = 1.0,
        drop_oldest_on_full: bool = False,
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
        self._offset_lock = asyncio.Lock()
        self._offset_trackers: Dict[Tuple[str, int], _PartitionOffsetTracker] = {}

    def _tracker_for(self, topic: str, partition: int, first_seen_offset: int) -> _PartitionOffsetTracker:
        key = (topic, int(partition))
        tr = self._offset_trackers.get(key)
        if tr is None:
            tr = _PartitionOffsetTracker()
            self._offset_trackers[key] = tr
        tr.ensure_initialized(int(first_seen_offset))
        return tr

    async def _mark_done_and_commit_if_possible(self, msg, *, skipped: bool = False) -> None:
        topic = msg.topic()
        partition = int(msg.partition())
        offset = int(msg.offset())

        async with self._offset_lock:
            tr = self._tracker_for(topic, partition, offset)
            tr.mark_done(offset)

            committable = tr.highest_contiguous_done()
            if committable is None:
                return

            tp = TopicPartition(topic, partition, committable + 1)
            try:
                await self.consumer.commit(offsets=[tp], asynchronous=False)
                tr.advance_after_commit(committable)

                if skipped:
                    logger.warning(
                        f"[{self.group_id}] skipped message committed "
                        f"(topic={topic}, partition={partition}, offset={offset})"
                    )
            except Exception:
                logger.exception(
                    f"[{self.group_id}] commit failed for topic={topic} "
                    f"partition={partition} next_offset={committable + 1}"
                )

    async def _worker_loop(self, queue: asyncio.Queue, handle_message):
        while True:
            msg = await queue.get()
            try:
                if msg is None:
                    return

                try:
                    await handle_message(msg)
                    await self._mark_done_and_commit_if_possible(msg)
                except Exception:
                    logger.exception(
                        f"[{self.group_id}] skip failed message "
                        f"(topic={msg.topic()}, partition={msg.partition()}, offset={msg.offset()})"
                    )
                    await self._mark_done_and_commit_if_possible(msg, skipped=True)

            except Exception:
                logger.exception(f"[{self.group_id}] unexpected worker error")
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
            f"[{self.group_id}] subscribed to {self.topic} "
            f"(max_pending_messages={self.max_pending_messages}, "
            f"worker_concurrency={self.worker_concurrency})"
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
                    logger.warning(
                        f"[{self.group_id}] dropped stale frame "
                        f"(topic={dropped.topic()}, partition={dropped.partition()}, offset={dropped.offset()})"
                    )
                    await self._mark_done_and_commit_if_possible(dropped, skipped=True)

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