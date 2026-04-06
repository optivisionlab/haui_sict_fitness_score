"""Background task: global Redis keyevent listener -> per-user channel republisher.

Subscribes to Redis keyspace events, detects flag transitions (0->1),
and publishes check-in notifications to per-user channels for SSE.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from app.core.redis import get_async_redis
from app.services.checkin_service import get_user_display_name, save_checkin_to_db

logger = logging.getLogger(__name__)


async def _dispatch_loop(stop_event: asyncio.Event, pattern: str = "__keyevent@0__:*") -> None:
    """Main dispatch loop: listen for keyevents, republish per-user."""
    redis = get_async_redis()
    pubsub = redis.pubsub()
    await pubsub.psubscribe(pattern)
    logger.info("Redis dispatcher subscribed to %s", pattern)

    prev_flag_snapshots: dict[str, dict[str, str]] = {}

    try:
        while not stop_event.is_set():
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                await asyncio.sleep(0.01)
                continue

            key = msg.get("data")
            if isinstance(key, bytes):
                key = key.decode()
            if not key or not isinstance(key, str) or not key.endswith(":data"):
                continue

            # Parse user from key
            user: Optional[str] = None
            if key.startswith("user:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    user = parts[1]

            # Read hash value
            try:
                ktype = await redis.type(key)
            except Exception:
                logger.exception("Failed to get type for key %s", key)
                continue

            if ktype != "hash":
                continue

            try:
                raw = await redis.hgetall(key)
                value = {
                    (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
                    for k, v in raw.items()
                }
            except Exception:
                logger.exception("Failed to read key %s", key)
                continue

            # Detect flag changes
            flag_fields = [f for f in value if f.startswith("flag")]
            prev_snapshot = prev_flag_snapshots.get(key, {})
            flag_updates = []

            for field in flag_fields:
                new_val = str(value.get(field, ""))
                old_val = str(prev_snapshot.get(field, ""))
                if new_val != old_val:
                    flag_updates.append({"flag": field, "old": old_val, "new": new_val})

            if not flag_updates:
                continue

            prev_flag_snapshots[key] = {f: str(value.get(f, "")) for f in flag_fields}

            camera_id = value.get("last_cam") or value.get("cam_id") or value.get("camera_id")
            ts_raw = value.get("last_time") or value.get("start_time")
            ts_iso = ts_raw if isinstance(ts_raw, str) else datetime.utcnow().isoformat()

            for item in flag_updates:
                if item["old"] == "1" or item["new"] != "1":
                    continue

                display_name = None
                if user:
                    try:
                        display_name = await get_user_display_name(user)
                    except Exception:
                        pass

                disp = display_name or (f"Người dùng {user}" if user else "Người dùng")
                message = f"Xin chào {disp}, bạn đã checkin thành công tại camera {camera_id} lúc {ts_iso}."
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
                            save_checkin_to_db(
                                user,
                                camera_id,
                                item["flag"],
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
                        logger.exception("Failed to publish global checkin event")

    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass


async def run_background(stop_event: asyncio.Event, pattern: str = "__keyevent@0__:*") -> None:
    """Entry point for background dispatcher task."""
    try:
        await _dispatch_loop(stop_event, pattern=pattern)
    except asyncio.CancelledError:
        logger.info("Redis dispatcher cancelled")
    except Exception:
        logger.exception("Redis dispatcher crashed")
