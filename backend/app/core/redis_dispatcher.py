import asyncio
import json
import logging
from typing import Optional

from app.core.database import get_async_redis

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

            # Only propagate core user payload keys (ignore lap locks, etc.)
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
                    value = await redis.hgetall(key)
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

            payload = {"key": key, "type": ktype, "value": value}

            if user:
                channel = f"user:{user}:channel"
                try:
                    await redis.publish(channel, json.dumps(payload, ensure_ascii=False))
                    logger.debug("Published event for user %s to %s", user, channel)
                except Exception:
                    logger.exception("Failed to publish to channel %s", channel)
            else:
                # if no user could be parsed, publish to a fallback channel for admins
                try:
                    await redis.publish("__global_redis_events__", json.dumps(payload, ensure_ascii=False))
                except Exception:
                    logger.exception("Failed to publish global redis event for key %s", key)

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
