"""Demo endpoint: global SSE stream with smart deduplication."""

import asyncio
import hashlib
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.redis import get_async_redis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events/global")
async def global_events(request: Request):
    """Global SSE endpoint streaming deduplicated Redis keyspace events."""
    return StreamingResponse(
        _global_sse_generator(request),
        media_type="text/event-stream",
    )


async def _global_sse_generator(request: Request) -> AsyncGenerator[str, None]:
    """Listen for hset events on user:*:data keys, deduplicate, and yield SSE."""
    logger.info("Starting global SSE stream (smart deduplication)")
    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()

    pattern = "__keyspace@0__:user:*:data"
    await pubsub.psubscribe(pattern)

    last_sent_hash: dict[str, str] = {}

    try:
        while True:
            if await request.is_disconnected():
                logger.info("Global SSE client disconnected")
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                channel_name = message.get("channel")
                action = message.get("data")

                if isinstance(channel_name, bytes):
                    channel_name = channel_name.decode()
                if isinstance(action, bytes):
                    action = action.decode()

                if action != "hset":
                    await asyncio.sleep(0.01)
                    continue

                real_key = channel_name.replace("__keyspace@0__:", "")
                parts = real_key.split(":")
                user_id = parts[1] if len(parts) > 1 else None

                if not user_id:
                    continue

                current_data = await redis_client.hgetall(real_key)
                decoded = {}
                if current_data:
                    for k, v in current_data.items():
                        dk = k.decode() if isinstance(k, bytes) else k
                        dv = v.decode() if isinstance(v, bytes) else v
                        decoded[dk] = dv

                response_payload = {
                    "user_id": user_id,
                    "start_time": decoded.get("start_time"),
                    "last_time": decoded.get("last_time"),
                    "last_cam": decoded.get("last_cam"),
                    "img_url": decoded.get("img_url"),
                    "step": decoded.get("step"),
                    "lap": decoded.get("lap"),
                }

                # Deduplication: only send if relevant fields changed
                compare_payload = {
                    "user_id": user_id,
                    "last_time": decoded.get("last_time"),
                    "last_cam": decoded.get("last_cam"),
                    "step": decoded.get("step"),
                    "lap": decoded.get("lap"),
                }
                current_hash = hashlib.md5(
                    json.dumps(compare_payload, sort_keys=True).encode()
                ).hexdigest()

                if last_sent_hash.get(user_id) == current_hash:
                    continue

                last_sent_hash[user_id] = current_hash
                yield f"data: {json.dumps(response_payload)}\n\n"

            await asyncio.sleep(0.01)

    except Exception as e:
        logger.error("Global SSE error: %s", e)
    finally:
        try:
            await pubsub.punsubscribe(pattern)
            await pubsub.close()
        except Exception:
            pass
