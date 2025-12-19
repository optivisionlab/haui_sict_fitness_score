from typing import AsyncGenerator, Optional
import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.core.database import get_async_redis, engine
from fastapi import Body
from sqlmodel import Session, select
from app.models.user import User
from app.models.camera import CameraUserClass
logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/events/user/{user_id}")
async def user_events(request: Request, user_id: str):
    """SSE endpoint that streams notifications for a specific user."""
    return StreamingResponse(
        _async_redis_sse_generator(request, user=user_id),
        media_type="text/event-stream",
    )


@router.post("/notify/user/{user_id}")
async def notify_user(user_id: str, payload: dict = Body(...)):
    """Publish a custom notification to a user's Redis channel.

     Body example: {"message": "Hello", "type": "custom"}
    """
    redis = get_async_redis()
    try:
        payload.setdefault("user_id", user_id)
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        await redis.publish(f"user:{user_id}:channel", json.dumps(payload, ensure_ascii=False))
        return {"status": "sent"}
    except Exception:
        logger.exception("Failed to publish manual notification to user %s", user_id)
        return {"status": "error"}


async def _get_user_display_name(user_id: str) -> Optional[str]:
    """Fetch user's full name or username synchronously via threadpool."""
    try:
        uid = int(user_id) if user_id and str(user_id).isdigit() else None
        if uid is None:
            return None

        def _sync_fetch():
            with Session(engine) as session:
                q = select(User).where(User.user_id == uid)
                res = session.exec(q)
                user_obj = res.one_or_none()
                if not user_obj:
                    return None
                return user_obj.full_name or user_obj.user_name or str(user_obj.user_id)

        return await asyncio.to_thread(_sync_fetch)
    except Exception:
        logger.exception("Failed to fetch user display name for %s", user_id)
        return None

async def _save_checkin_to_db(
    user_id: str,
    camera_id: Optional[str],
    flag_name: str,
    timestamp: str,
    image_url: Optional[str] = None,
    lap: Optional[str] = None,
    avg_speed: Optional[str] = None,
    exam_id: Optional[str] = None,
    class_id: Optional[str] = None,
):
    """Persist a check-in record with optional telemetry and media reference."""
    try:
        uid = int(user_id) if user_id and str(user_id).isdigit() else None
        cam_id = int(camera_id) if camera_id and str(camera_id).isdigit() else None
        ex_id = int(exam_id) if exam_id and str(exam_id).isdigit() else None
        cls_id = int(class_id) if class_id and str(class_id).isdigit() else None

        # convert timestamp string to datetime if possible
        checkin_dt = None
        try:
            if isinstance(timestamp, str):
                checkin_dt = datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, datetime):
                checkin_dt = timestamp
        except Exception:
            checkin_dt = datetime.utcnow()

        def _sync_save():
            with Session(engine) as session:
                if uid is None or cam_id is None:
                    return

                # ensure camera exists (create minimal record if not)
                try:
                    from app.models import Camera
                except Exception:
                    Camera = None

                if cam_id is not None and Camera is not None:
                    existing = session.get(Camera, cam_id)
                    if existing is None:
                        # create a minimal camera record so foreign key constraint satisfied
                        cam = Camera(camera_id=cam_id, camera_name=f"Camera {cam_id}")
                        session.add(cam)
                        session.commit()

                # best-effort numeric conversions for optional telemetry fields
                lap_val = None
                try:
                    if lap is not None:
                        lap_val = int(lap)
                except Exception:
                    lap_val = None

                avg_speed_val = None
                try:
                    if avg_speed is not None:
                        avg_speed_val = float(avg_speed)
                except Exception:
                    avg_speed_val = None

                record = CameraUserClass(
                    user_id=uid,
                    camera_id=cam_id,
                    class_id=cls_id,
                    exam_id=ex_id,
                    lap=lap_val if lap_val is not None else 1,
                    avg_speed=avg_speed_val,
                    flag=flag_name,
                    checkin_time=checkin_dt,
                    image_url=image_url,
                )
                session.add(record)
                session.commit()

        await asyncio.to_thread(_sync_save)
    except Exception as exc:
        # If DB integration not available or fails, log and continue
        logger.exception("Failed to save checkin to DB: %s", exc)


async def _async_redis_sse_generator(request: Request, *, pattern: Optional[str] = None, user: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Async generator that listens for either keyevent patterns or per-user channels. """
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

    # keep last-known flag states per key so we can detect transitions
    prev_flags = {}

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                if subscribe_pattern:
                    key = message.get("data")
                    if isinstance(key, bytes):
                        try:
                            key = key.decode()
                        except Exception:
                            key = None
                    if key:
                        # Only forward user hash records (ignore auxiliary keys such as lap locks)
                        if not str(key).endswith(":data"):
                            continue
                        try:
                            ktype = await redis_client.type(key)
                        except Exception as e:
                            payload = {"key": key, "error": str(e)}
                            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                            continue

                        try:
                            if ktype == "hash":
                                raw = await redis_client.hgetall(key)
                                # normalize bytes -> str
                                value = {}
                                for k, v in (raw.items() if isinstance(raw, dict) else []):
                                    if isinstance(k, bytes):
                                        k = k.decode()
                                    if isinstance(v, bytes):
                                        v = v.decode()
                                    value[k] = v
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

                        # detect flag changes only for hashes
                        if ktype == "hash" and isinstance(value, dict):
                            flag_fields = [f for f in value.keys() if f.startswith("flag")]
                            prev = prev_flags.get(key, {})
                            user_id = None
                            # try parse user id from key like "user:13:data"
                            try:
                                parts = key.split(":")
                                if len(parts) >= 2 and parts[0] == "user":
                                    user_id = parts[1]
                            except Exception:
                                pass
                            camera_id = value.get("last_cam") or value.get("cam_id") or value.get("camera_id")

                            for f in flag_fields:
                                old = str(prev.get(f, ""))
                                new = str(value.get(f, ""))
                                if old == "1" and new == "1":
                                    continue
                                if old != "1" and new == "1":
                                    ts = value.get("start_time") or datetime.utcnow().isoformat()
                                    
                                    display_name = None
                                    if user_id:
                                        display_name = await _get_user_display_name(user_id)

                                    disp = display_name or (f"Người dùng {user_id}" if user_id else "Người dùng")

                                    lap_raw = (
                                        value.get("lap")
                                        or value.get("lap_count")
                                        or value.get("laps")
                                    )
                                    lap_numeric = None
                                    if lap_raw is not None:
                                        try:
                                            lap_numeric = int(float(str(lap_raw)))
                                        except Exception:
                                            lap_numeric = None

                                    base_message = (
                                        f"Xin chào {disp}, bạn đã checkin thành công tại camera {camera_id} lúc {ts}."
                                    )
                                    lap_suffix = (
                                        f" Số vòng đã hoàn thành: {lap_numeric}."
                                        if lap_numeric is not None
                                        else ""
                                    )
                                    message = f"{base_message}{lap_suffix}"

                                    evt = {"message": message}

                                    try:
                                        if user_id:
                                            await redis_client.publish(
                                                f"user:{user_id}:channel",
                                                json.dumps(
                                                    {"type": "checkin", "message": message},
                                                    ensure_ascii=False,
                                                ),
                                            )
                                    except Exception:
                                        logger.exception("Failed to publish checkin event for user %s", user_id)

                                    try:
                                        asyncio.create_task(
                                            _save_checkin_to_db(
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

                                    yield f"event: checkin\ndata: {json.dumps(evt, ensure_ascii=False)}\n\n"

                            if flag_fields:
                                prev_flags[key] = {f: str(value.get(f, "")) for f in flag_fields}
                else:
                    # channel-mode: message['data'] is already the payload string
                    data = message.get("data")
                    if isinstance(data, bytes):
                        try:
                            data = data.decode()
                        except Exception:
                            data = None
                    if data:
                        try:
                            payload_obj = json.loads(data)
                        except Exception:
                            payload_obj = None

                        if not payload_obj or not isinstance(payload_obj, dict):
                            continue

                        key_val = payload_obj.get("key")
                        if key_val and not str(key_val).endswith(":data"):
                            continue

                        evt_type = payload_obj.get("type")
                        message_text = payload_obj.get("message")
                        if not message_text:
                            continue

                        serialized = json.dumps({"message": message_text}, ensure_ascii=False)

                        if evt_type == "checkin":
                            yield f"event: checkin\ndata: {serialized}\n\n"
                            continue

                        if evt_type != "flag_update":
                            continue

                        yield f"event: flag_update\ndata: {serialized}\n\n"

            # cooperative sleep so other tasks can run
            await asyncio.sleep(0.01)
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
        except Exception:
            pass
