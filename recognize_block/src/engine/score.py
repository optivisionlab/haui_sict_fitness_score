from __future__ import annotations

import time
from typing import Optional

from loguru import logger
from src.config.config import EvalConfig, EVAL_CONFIG
from src.depend.depend import minio_client
from datetime import datetime


def _decode(v):
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        try:
            return v.decode("utf-8")
        except Exception:
            return str(v)
    return v


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
        self.cfg = config or EVAL_CONFIG
        self._checkin_and_lap_script = self.redis_client.register_script(
            """
            local key = KEYS[1]

            if redis.call('EXISTS', key) == 0 then
                return {-2, -1}
            end

            if redis.call('HGET', key, 'state') ~= 'active' then
                return {-1, -1}
            end

            local cam_id = ARGV[1]
            local last_time = ARGV[2]
            local img_url = ARGV[3]
            local n = tonumber(ARGV[4])

            local redis_last_cam = redis.call('HGET', key, 'last_cam') or ''

            if redis_last_cam == cam_id then
                return {0, tonumber(redis.call('HGET', key, 'lap') or '0')}
            end

            local current_flag = tonumber(redis.call('HGET', key, 'flag_' .. cam_id) or '0')
            if current_flag == 1 then
                return {0, tonumber(redis.call('HGET', key, 'lap') or '0')}
            end

            -- set current check-in state
            redis.call('HSET', key, 'flag_' .. cam_id, 1)
            redis.call('HSET', key, 'last_cam', cam_id)
            redis.call('HSET', key, 'last_time', last_time)

            if img_url ~= '' then
                redis.call('HSET', key, 'img_url', img_url)
            end

            -- check all flags
            for i = 1, n do
                local field = ARGV[i + 4]
                if tonumber(redis.call('HGET', key, field) or '0') ~= 1 then
                    local lap_now = tonumber(redis.call('HGET', key, 'lap') or '0')
                    return {1, lap_now}
                end
            end

            -- all flags done => increment lap and reset flags
            local lap = tonumber(redis.call('HGET', key, 'lap') or '0') + 1
            redis.call('HSET', key, 'lap', lap)

            for i = 1, n do
                redis.call('HSET', key, ARGV[i + 4], 0)
            end

            return {2, lap}
            """
        )
        logger.info("Evaluator initialized with config: {}", self.cfg.upload_each_checkin)

    @staticmethod
    def _to_redis_datetime_str_from_ms(ts_ms: float) -> str:
        return datetime.fromtimestamp(ts_ms / 1000.0).isoformat(timespec="milliseconds")

    @staticmethod
    def _from_redis_datetime_str(value):
        raw = _decode(value)
        if not raw:
            return None
        return datetime.fromisoformat(str(raw))
    
    def _ensure_user_key_if_test(self, key_user: str, timestamp: float, cam_id: str):
        if not self.test_mode:
            return
        if self.redis_client.exists(key_user):
            return

        start_time_str = self._to_redis_datetime_str_from_ms(timestamp)

        mapping = {
            "state": "active",
            "exam_id": -1,
            "step": 0,
            "lap": 0,
            "start_time": start_time_str,
            "last_cam": cam_id,
            "last_time": start_time_str,
            "img_url": "",
            **{f"flag_{c}": 0 for c in self.id_run_process},
        }
        mapping[f"flag_{cam_id}"] = 1

        self.redis_client.hset(key_user, mapping=mapping)
        logger.warning("[TEST_MODE] init redis key with first cam {} for {}", cam_id, key_user)
    

    def set_flag_and_check_lap_redis(self, user_id, cam_id, copy_frame=None, timestamp=None):
        """
        One atomic Redis operation:
        - set current camera flag
        - update last_cam / last_time / img_url
        - if all flags are set, increment lap and reset flags
        Returns:
            (-2, -1): key not found
            (-1, -1): state not active
            (0, lap): same cam duplicate
            (1, lap): check-in success, lap not completed
            (2, lap): lap completed
        """
        user_id = str(user_id)
        cam_id = str(cam_id)

        if timestamp is not None:
            ts_ms = float(timestamp)
        else:
            ts_ms = time.time_ns() / 1_000_000.0

        key_user = f"user:{user_id}:data"

        self._ensure_user_key_if_test(key_user, ts_ms, cam_id=cam_id)

        if not self.test_mode and not self.redis_client.exists(key_user):
            return (-2, -1)

        # Không đọc last_cam ở Python nữa.
        # last_cam = _decode(self.redis_client.hget(key_user, "last_cam")) or ""

        img_url = ""
        if self.cfg.upload_each_checkin and copy_frame is not None:
            try:
                dt = datetime.fromtimestamp(ts_ms / 1000.0)
                destination_file = dt.strftime(f"%Y/%m/%d/%H/%M/%S/{user_id}.jpg")
                img_url = minio_client.push_data(
                    image=copy_frame,
                    destination_file=destination_file,
                )
            except Exception as e:
                logger.exception("MinIO upload failed for user {}: {}", user_id, e)

        flag_fields = [f"flag_{c}" for c in self.id_run_process]

        result = self._checkin_and_lap_script(
            keys=[key_user],
            args=[
                cam_id,
                # str(last_cam),
                self._to_redis_datetime_str_from_ms(ts_ms),
                img_url,
                str(len(flag_fields)),
                *flag_fields,
            ],
        )

        status = int(result[0])
        lap = int(result[1])

        if status == -2:
            logger.warning("User key not found for {}", user_id)
        elif status == -1:
            logger.warning("User {} is not active", user_id)
        elif status == 0:
            logger.debug("User {} duplicate same cam {}", user_id, cam_id)
        elif status == 1:
            logger.debug("User {} set flag cam {} (lap not completed)", user_id, cam_id)
        elif status == 2:
            logger.info("User {} completed lap {}", user_id, lap)

        return status, lap
