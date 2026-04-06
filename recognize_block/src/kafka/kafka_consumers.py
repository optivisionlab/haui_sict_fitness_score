import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple

from confluent_kafka import KafkaException, TopicPartition
from confluent_kafka.aio import AIOConsumer
from loguru import logger
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

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
        stats_file_path: Optional[str] = None,
        stats_flush_interval: float = 5.0,
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
        self.received_count = 0
        self.enqueued_count = 0
        self.processed_count = 0
        self.failed_count = 0
        self.dropped_on_full_count = 0   # cái bạn đang cần
        self.skipped_failed_count = 0    # skip do xử lý lỗi, khác với drop_oldest
        self.max_queue_size_seen = 0

        self.stats_file_path = stats_file_path or f"{self.group_id}_consumer_stats.txt"
        self.stats_flush_interval = max(1.0, float(stats_flush_interval))
        self._stats_file_lock = asyncio.Lock()
        self._stats_flush_task: Optional[asyncio.Task] = None

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

    def _build_stats_text(self) -> str:
        return "\n".join([
            f"timestamp={datetime.now().isoformat()}",
            f"group_id={self.group_id}",
            f"topic={self.topic}",
            f"received_count={self.received_count}",
            f"enqueued_count={self.enqueued_count}",
            f"processed_count={self.processed_count}",
            f"failed_count={self.failed_count}",
            f"dropped_on_full_count={self.dropped_on_full_count}",
            f"max_queue_size_seen={self.max_queue_size_seen}",
            ""
        ])

    async def _flush_stats_to_file(self) -> None:
        async with self._stats_file_lock:
            Path(self.stats_file_path).write_text(
                self._build_stats_text(),
                encoding="utf-8"
            )

    async def _stats_flush_loop(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(self.stats_flush_interval)
                # comment nếu không ghi file nữa
                await self._flush_stats_to_file()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(f"[{self.group_id}] failed to flush stats file")

    async def _worker_loop(self, queue: asyncio.Queue, handle_message):
        while True:
            msg = await queue.get()
            try:
                if msg is None:
                    return

                try:
                    await handle_message(msg)
                    self.processed_count += 1
                    await self._mark_done_and_commit_if_possible(msg)
                except Exception:
                    self.failed_count += 1
                    self.skipped_failed_count += 1
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
        self._stats_flush_task = asyncio.create_task(self._stats_flush_loop())

        queue: asyncio.Queue = asyncio.Queue(maxsize=self.max_pending_messages)
        workers = [
            asyncio.create_task(self._worker_loop(queue, handle_message))
            for _ in range(self.worker_concurrency)
        ]

        logger.info(
            f"[{self.group_id}] subscribed to {self.topic} "
            f"(max_pending_messages={self.max_pending_messages}, "
            f"worker_concurrency={self.worker_concurrency}, "
            f"drop_oldest_on_full={self.drop_oldest_on_full})"
        )

        try:
            while self.running:
                msg = await self.consumer.poll(self.poll_timeout)
                if msg is None:
                    continue
                if msg.error():
                    raise KafkaException(msg.error())
                self.received_count += 1

                if queue.qsize() > self.max_queue_size_seen:
                    self.max_queue_size_seen = queue.qsize()

                if queue.full() and self.drop_oldest_on_full:
                    dropped = queue.get_nowait()
                    queue.task_done()
                    self.dropped_on_full_count += 1
                    logger.warning(
                        f"[{self.group_id}] dropped stale frame "
                        f"(topic={dropped.topic()}, partition={dropped.partition()}, offset={dropped.offset()})"
                    )
                    await self._mark_done_and_commit_if_possible(dropped, skipped=True)

                await queue.put(msg)
                self.enqueued_count += 1

                if queue.qsize() > self.max_queue_size_seen:
                    self.max_queue_size_seen = queue.qsize()

        finally:
            self.running = False
            if self._stats_flush_task is not None:
                self._stats_flush_task.cancel()
                await asyncio.gather(self._stats_flush_task, return_exceptions=True)

            await queue.join()

            for _ in workers:
                await queue.put(None)

            await asyncio.gather(*workers, return_exceptions=True)
            await self._flush_stats_to_file()
            logger.info(
                f"[{self.group_id}] final stats: "
                f"received={self.received_count}, "
                f"enqueued={self.enqueued_count}, "
                f"processed={self.processed_count}, "
                f"failed={self.failed_count}, "
                f"dropped_on_full={self.dropped_on_full_count}, "
                f"max_queue_size_seen={self.max_queue_size_seen}, "
                f"stats_file={self.stats_file_path}"
            )
            await self.consumer.close()

    def stop(self):
        self.running = False