"""Redis SSE endpoints for real-time user notifications."""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Body, Request
from fastapi.responses import StreamingResponse

from app.core.redis import get_async_redis
from app.services.checkin_service import get_user_display_name, save_checkin_to_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events/user/{user_id}")
async def user_events(request: Request, user_id: str):
    """SSE endpoint that streams notifications for a specific user."""
    return StreamingResponse(
        _user_sse_generator(request, user=user_id),
        media_type="text/event-stream",
    )


@router.post("/notify/user/{user_id}")
async def notify_user(user_id: str, payload: dict = Body(...)):
    """Publish a custom notification to a user's Redis channel."""
    redis = get_async_redis()
    try:
        payload.setdefault("user_id", user_id)
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        await redis.publish(f"user:{user_id}:channel", json.dumps(payload, ensure_ascii=False))
        return {"status": "sent"}
    except Exception:
        logger.exception("Failed to publish notification to user %s", user_id)
        return {"status": "error"}


async def _user_sse_generator(
    request: Request,
    *,
    pattern: Optional[str] = None,
    user: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Async generator for SSE: listens to keyevent patterns or per-user channels."""
    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()

    use_pattern = pattern is not None
    if use_pattern:
        await pubsub.psubscribe(pattern)
    else:
        channel = f"user:{user}:channel" if user else "__global_redis_events__"
        await pubsub.subscribe(channel)

    prev_flags: dict[str, dict[str, str]] = {}

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                if use_pattern:
                    async for event in _handle_pattern_message(redis_client, message, prev_flags):
                        yield event
                else:
                    event = _handle_channel_message(message)
                    if event:
                        yield event

            await asyncio.sleep(0.01)
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass


async def _handle_pattern_message(
    redis_client, message: dict, prev_flags: dict
) -> AsyncGenerator[str, None]:
    """Process a keyevent pattern message: detect flag changes, yield SSE events."""
    key = message.get("data")
    if isinstance(key, bytes):
        key = key.decode()
    if not key or not isinstance(key, str) or not key.endswith(":data"):
        return

    try:
        ktype = await redis_client.type(key)
    except Exception as e:
        yield f"data: {json.dumps({'key': key, 'error': str(e)}, ensure_ascii=False)}\n\n"
        return

    if ktype != "hash":
        return

    try:
        raw = await redis_client.hgetall(key)
        value = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in raw.items()
        }
    except Exception as e:
        yield f"data: {json.dumps({'key': key, 'error': str(e)}, ensure_ascii=False)}\n\n"
        return

    # Parse user from key like "user:13:data"
    user_id: Optional[str] = None
    parts = key.split(":")
    if len(parts) >= 2 and parts[0] == "user":
        user_id = parts[1]

    camera_id = value.get("last_cam") or value.get("cam_id") or value.get("camera_id")
    flag_fields = [f for f in value if f.startswith("flag")]
    prev = prev_flags.get(key, {})

    for f in flag_fields:
        old = str(prev.get(f, ""))
        new = str(value.get(f, ""))

        if old == "1" and new == "1":
            continue
        if old != "1" and new == "1":
            ts = value.get("start_time") or datetime.utcnow().isoformat()

            display_name = None
            if user_id:
                display_name = await get_user_display_name(user_id)
            disp = display_name or (f"Người dùng {user_id}" if user_id else "Người dùng")

            lap_raw = value.get("lap") or value.get("lap_count") or value.get("laps")
            lap_numeric = None
            if lap_raw is not None:
                try:
                    lap_numeric = int(float(str(lap_raw)))
                except (TypeError, ValueError):
                    pass

            message_text = f"Xin chào {disp}, bạn đã checkin thành công tại camera {camera_id} lúc {ts}."
            if lap_numeric is not None:
                message_text += f" Số vòng đã hoàn thành: {lap_numeric}."

            # Publish to user channel
            if user_id:
                try:
                    await redis_client.publish(
                        f"user:{user_id}:channel",
                        json.dumps({"type": "checkin", "message": message_text}, ensure_ascii=False),
                    )
                except Exception:
                    logger.exception("Failed to publish checkin for user %s", user_id)

            # Save to DB
            try:
                asyncio.create_task(
                    save_checkin_to_db(
                        user_id or "",
                        camera_id,
                        f,
                        ts,
                        image_url=value.get("img_url") or value.get("image_url"),
                        lap=value.get("lap"),
                        avg_speed=value.get("avg_speed"),
                        exam_id=value.get("exam_id"),
                        class_id=value.get("class_id"),
                    )
                )
            except Exception:
                logger.exception("Failed to schedule DB save task")

            yield f"event: checkin\ndata: {json.dumps({'message': message_text}, ensure_ascii=False)}\n\n"

    if flag_fields:
        prev_flags[key] = {f: str(value.get(f, "")) for f in flag_fields}


def _handle_channel_message(message: dict) -> Optional[str]:
    """Process a channel-mode message: return SSE string or None."""
    data = message.get("data")
    if isinstance(data, bytes):
        data = data.decode()
    if not data:
        return None

    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    key_val = payload.get("key")
    if key_val and not str(key_val).endswith(":data"):
        return None

    message_text = payload.get("message")
    if not message_text:
        return None

    evt_type = payload.get("type")
    serialized = json.dumps({"message": message_text}, ensure_ascii=False)

    if evt_type == "checkin":
        return f"event: checkin\ndata: {serialized}\n\n"
    if evt_type == "flag_update":
        return f"event: flag_update\ndata: {serialized}\n\n"

    return None
