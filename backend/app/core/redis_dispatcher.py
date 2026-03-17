import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from app.core.database import get_async_redis
from app.api.endpoints.redis_events import _get_user_display_name, _save_checkin_to_db

logger = logging.getLogger(__name__)


async def _dispatch_loop(stop_event: asyncio.Event, pattern: str = "__keyevent@0__:*") -> None:
    """Global Redis listener: subscribes to keyevents and republishes per-user channels.

    - Listens for key events (e.g., hset on user:<name>:data)
    - Extracts the user identifier from the key (expects `user:<user>:...`)
    - Reads the key value and publishes a JSON payload to channel `user:<user>:channel`

    This design keeps a single global subscriber (low cost) and broadcasts only
    relevant messages to per-user channels which client SSE connections subscribe to.
    """
    redis = get_async_redis()
    pubsub = redis.pubsub()
    await pubsub.psubscribe(pattern)
    logger.info("Redis dispatcher subscribed to %s", pattern)

    # Remember previous flag values per key to suppress duplicate broadcasts
    prev_flag_snapshots: dict[str, dict[str, str]] = {}

    try:
        while not stop_event.is_set():
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                await asyncio.sleep(0.01)
                continue

            # msg example: {'type': 'pmessage', 'pattern': '__keyevent@0__:*', 'channel': '__keyevent@0__:hset', 'data': 'user:Cuong:data'}
            key = msg.get("data")
            if isinstance(key, bytes):
                try:
                    key = key.decode()
                except Exception:
                    key = None
            if not key or not isinstance(key, str):
                continue

            # Only propagate core user payload keys (ignore auxiliary keys such as lap locks)
            if not key.endswith(":data"):
                continue

            # try to parse user from key (pattern: user:<user>:...)
            user: Optional[str] = None
            if key.startswith("user:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    user = parts[1]

            # read key value (best-effort)
            try:
                ktype = await redis.type(key)
            except Exception as e:
                logger.exception("Failed to get type for key %s: %s", key, e)
                ktype = "unknown"

            value = None
            try:
                if ktype == "hash":
                    raw = await redis.hgetall(key)
                    # normalize bytes to strings for downstream comparisons
                    value = {}
                    for raw_k, raw_v in (raw.items() if isinstance(raw, dict) else []):
                        if isinstance(raw_k, bytes):
                            raw_k = raw_k.decode()
                        if isinstance(raw_v, bytes):
                            raw_v = raw_v.decode()
                        value[raw_k] = raw_v
                elif ktype == "string":
                    value = await redis.get(key)
                elif ktype == "list":
                    value = await redis.lrange(key, 0, -1)
                elif ktype == "set":
                    value = list(await redis.smembers(key))
                elif ktype == "zset":
                    value = await redis.zrange(key, 0, -1, withscores=True)
                else:
                    value = None
            except Exception as e:
                logger.exception("Failed to read key %s: %s", key, e)
                value = {"error": str(e)}

            # No change detection possible without hash data
            if not isinstance(value, dict):
                continue

            # Skip publish if no flag value changed compared to previous snapshot
            flag_fields = [f for f in value if f.startswith("flag")]
            prev_snapshot = prev_flag_snapshots.get(key, {})
            flag_changed = False
            flag_updates = []
            for field in flag_fields:
                new_val = str(value.get(field, ""))
                old_val = str(prev_snapshot.get(field, ""))
                if new_val != old_val:
                    flag_changed = True
                    flag_updates.append({"flag": field, "old": old_val, "new": new_val})

            if not flag_changed:
                continue

            prev_flag_snapshots[key] = {f: str(value.get(f, "")) for f in flag_fields}

            camera_id = value.get("last_cam") or value.get("cam_id") or value.get("camera_id")
            timestamp_raw = value.get("last_time") or value.get("start_time")
            ts_iso = timestamp_raw if isinstance(timestamp_raw, str) else datetime.utcnow().isoformat()

            messages = []
            for item in flag_updates:
                if item["old"] == "1" or item["new"] != "1":
                    continue

                display_name = None
                if user:
                    try:
                        display_name = await _get_user_display_name(user)
                    except Exception:
                        display_name = None

                disp = display_name or (f"Người dùng {user}" if user else "Người dùng")
                message = f"Xin chào {disp}, bạn đã checkin thành công tại camera {camera_id} lúc {ts_iso}."
                messages.append((message, ts_iso, item["flag"]))

            for message, ts_iso, flag_name in messages:
                payload = {"type": "checkin", "message": message}
                if user:
                    channel = f"user:{user}:channel"
                    try:
                        await redis.publish(channel, json.dumps(payload, ensure_ascii=False))
                        logger.debug("Published checkin for user %s to %s", user, channel)
                    except Exception:
                        logger.exception("Failed to publish checkin to channel %s", channel)

                    try:
                        asyncio.create_task(
                            _save_checkin_to_db(
                                user,
                                camera_id,
                                flag_name,
                                ts_iso,
                                image_url=value.get("img_url") or value.get("image_url"),
                                lap=value.get("lap"),
                                avg_speed=value.get("avg_speed"),
                            )
                        )
                    except Exception:
                        logger.exception("Failed to schedule DB persistence for user %s", user)
                else:
                    try:
                        await redis.publish("__global_redis_events__", json.dumps(payload, ensure_ascii=False))
                    except Exception:
                        logger.exception("Failed to publish global checkin event for key %s", key)

    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass


async def run_background(stop_event: asyncio.Event, pattern: str = "__keyevent@0__:*") -> None:
    try:
        await _dispatch_loop(stop_event, pattern=pattern)
    except asyncio.CancelledError:
        logger.info("Redis dispatcher cancelled")
    except Exception:
        logger.exception("Redis dispatcher crashed")
