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
        if not self.redis_client.exists(key_user):
            return False

        lap_lock = f"user:{user_id}:lap_lock"
        locked = self.redis_client.set(lap_lock, 1, nx=True, ex=self.cfg.lap_lock_seconds)
        if not locked:
            return False

        if _decode(self.redis_client.hget(key_user, "state")) != "active":
            return False

        pipe = self.redis_client.pipeline()
        for c in self.id_run_process:
            pipe.hget(key_user, f"flag_{c}")
        flags_raw = pipe.execute()
        flags = [int(_decode(v) or 0) for v in flags_raw]
        if not all(flags):
            return False

        lap_number = int(_decode(self.redis_client.hget(key_user, "lap")) or 0) + 1
        reset_map = {f"flag_{c}": 0 for c in self.id_run_process}

        pipe = self.redis_client.pipeline()
        pipe.hset(key_user, "lap", lap_number)
        pipe.hset(key_user, mapping=reset_map)
        pipe.execute()

        logger.info("User {} completed lap {}", user_id, lap_number)
        return True


class GlobalEvaluator(SetUpEvaluate):
    """Backward-compatible evaluator. Extend here if you want DB writes."""
    pass