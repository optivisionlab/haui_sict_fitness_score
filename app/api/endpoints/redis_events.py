from typing import AsyncGenerator, Optional
import json
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.database import get_async_redis

router = APIRouter()


async def _async_redis_sse_generator(request: Request, *, pattern: Optional[str] = None, user: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Async generator that listens for either keyevent patterns or per-user channels.

    Behavior:
      - If `pattern` is provided, uses psubscribe(pattern) and yields events based on
        keyevent notifications (legacy behavior).
      - If `user` is provided, subscribes to channel `user:<user>:channel` and yields
        payloads published by the dispatcher.
      - If neither is provided, subscribes to the global admin channel `__global_redis_events__`.
    """
    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()

    subscribe_pattern = pattern is not None
    channel_name = None
    if subscribe_pattern:
        await pubsub.psubscribe(pattern)
    else:
        if user:
            channel_name = f"user:{user}:channel"
        else:
            channel_name = "__global_redis_events__"
        await pubsub.subscribe(channel_name)

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                # For pattern-mode we receive key strings in `data` and proceed to read
                # the key directly (legacy). For channel-mode the publisher will send
                # a JSON payload string which we forward directly.
                if subscribe_pattern:
                    key = message.get("data")
                    if key:
                        try:
                            ktype = await redis_client.type(key)
                        except Exception as e:
                            payload = {"key": key, "error": str(e)}
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                            continue

                        try:
                            if ktype == "hash":
                                value = await redis_client.hgetall(key)
                            elif ktype == "string":
                                value = await redis_client.get(key)
                            elif ktype == "list":
                                value = await redis_client.lrange(key, 0, -1)
                            elif ktype == "set":
                                value = list(await redis_client.smembers(key))
                            elif ktype == "zset":
                                value = await redis_client.zrange(key, 0, -1, withscores=True)
                            else:
                                value = None
                        except Exception as e:
                            payload = {"key": key, "error": f"failed to read key: {e}"}
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                            continue

                        payload = {"key": key, "type": ktype, "value": value}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    # channel-mode: message['data'] is already the payload string
                    data = message.get("data")
                    # redis-py may return bytes depending on decode settings
                    if isinstance(data, bytes):
                        try:
                            data = data.decode()
                        except Exception:
                            data = None
                    if data:
                        # forward raw payload as-is (but wrap as SSE data field)
                        yield f"data: {data}\n\n"

            # cooperative sleep so other tasks can run
            await asyncio.sleep(0.01)
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass


@router.get("/subscribe")
def subscribe_redis_events(request: Request, pattern: Optional[str] = None, user: Optional[str] = None):
    """SSE endpoint that streams Redis key events.

    Query params:
      - pattern: optional keyevent pattern to subscribe (default: __keyevent@0__:* )

    Example:
      GET /api/v1/redis/subscribe?pattern=__keyevent@0__:hset
    """
    if pattern:
        p = pattern
        return StreamingResponse(_async_redis_sse_generator(request, pattern=p), media_type="text/event-stream")
    return StreamingResponse(_async_redis_sse_generator(request, user=user), media_type="text/event-stream")


@router.get("/ping")
async def ping_redis():
    client = get_async_redis()
    try:
        pong = await client.ping()
        return {"ok": bool(pong)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
