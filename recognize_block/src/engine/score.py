from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger
from src.depend.depend import minio_client


def _decode(v):
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return str(v)
    return v


@dataclass
class EvalConfig:
    upload_each_checkin: bool = False
    # minimum interval (in milliseconds) between two valid check-ins of the same user
    checkin_cooldown_ms: int = 500
    lap_lock_seconds: int = 2


class SetUpEvaluate:
    """Write camera flags to Redis and compute laps (no DB write)."""

    def __init__(
        self,
        id_run_process,
        redis_client=None,
        pg_handler=None,
        test_mode: bool = False,
        *,
        config: Optional[EvalConfig] = None,
    ):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client
        self.pg_handler = pg_handler
        self.test_mode = test_mode
        self.cfg = config or EvalConfig()
        self._lap_script = self.redis_client.register_script(
            """
            local key = KEYS[1]
            if redis.call('EXISTS', key) == 0 then
                return -2
            end

            if redis.call('HGET', key, 'state') ~= 'active' then
                return -1
            end

            local n = tonumber(ARGV[1])
            for i = 1, n do
                local field = ARGV[i + 1]
                if tonumber(redis.call('HGET', key, field) or '0') ~= 1 then
                    return 0
                end
            end

            local lap = tonumber(redis.call('HGET', key, 'lap') or '0') + 1
            redis.call('HSET', key, 'lap', lap)

            for i = 1, n do
                redis.call('HSET', key, ARGV[i + 1], 0)
            end

            return lap
            """
        )

    def _ensure_user_key_if_test(self, key_user: str, timestamp: float):
        if not self.test_mode:
            return
        if self.redis_client.exists(key_user):
            return
        self.redis_client.hset(
            key_user,
            mapping={
                "state": "active",
                "exam_id": -1,
                "step": 0,
                "lap": 0,
                "start_time": timestamp,
                "last_cam": "",
                "last_time": 0,
                "img_url": "",
                **{f"flag_{c}": 0 for c in self.id_run_process},
            },
        )
        logger.warning("[TEST_MODE] init redis key for {}", key_user)

    def set_flag_redis(self, user_id, cam_id, copy_frame=None, timestamp=None) -> bool:
        user_id = str(user_id)
        cam_id = str(cam_id)
        # work in milliseconds for incoming timestamps; fall back to current time in ms
        if timestamp is not None:
            ts_ms = float(timestamp)
        else:
            ts_ms = time.time_ns() / 1_000_000.0
        key_user = f"user:{user_id}:data"

        # ensure key exists (using ms-based timestamp)
        self._ensure_user_key_if_test(key_user, ts_ms)

        if not self.test_mode:
            if not self.redis_client.exists(key_user):
                return False
            if _decode(self.redis_client.hget(key_user, "state")) != "active":
                return False

        # read last_cam + last_time in one RTT
        pipe = self.redis_client.pipeline()
        pipe.hget(key_user, "last_cam")
        pipe.hget(key_user, "last_time")
        last_cam, last_time = pipe.execute()
        last_cam = str(_decode(last_cam) or "")
        last_time_ms = float(_decode(last_time) or 0)

        # Dedup: same cam repeated OR too close in time
        if last_cam == cam_id:
            return False
        # reject if too close in time (all in milliseconds)
        if ts_ms - last_time_ms < self.cfg.checkin_cooldown_ms:
            return False

        pipe = self.redis_client.pipeline()
        pipe.hset(key_user, f"flag_{cam_id}", 1)
        pipe.hset(key_user, "last_cam", cam_id)
        pipe.hset(key_user, "last_time", ts_ms)

        # Optional (expensive): upload proof image
        if self.cfg.upload_each_checkin and copy_frame is not None:
            try:
                img_url = minio_client.push_data(
                    image=copy_frame,
                    destination_file=f"{int(ts_ms)}/{user_id}.jpg",
                )
                pipe.hset(key_user, "img_url", img_url)
            except Exception as e:
                logger.warning("MinIO upload failed for user {}: {}", user_id, e)

        pipe.execute()
        logger.debug("User {} set flag cam {}", user_id, cam_id)
        return True

    def check_lap_1_user(self, user_id) -> bool:
        user_id = str(user_id)
        key_user = f"user:{user_id}:data"
        flag_fields = [f"flag_{c}" for c in self.id_run_process]

        # Atomic finalize in Redis: only increment lap when all flags are set,
        # and reset flags in the same operation to avoid race conditions.
        result = int(
            self._lap_script(
                keys=[key_user],
                args=[str(len(flag_fields)), *flag_fields],
            )
        )

        if result <= 0:
            return False

        logger.info("User {} completed lap {}", user_id, result)
        return True


class GlobalEvaluator(SetUpEvaluate):
    """Backward-compatible evaluator. Extend here if you want DB writes."""
    pass