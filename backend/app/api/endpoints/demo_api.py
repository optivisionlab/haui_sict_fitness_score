from typing import AsyncGenerator
import json
import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.core.database import get_async_redis

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/events/global")
async def global_events(request: Request):
    return StreamingResponse(_async_global_sse_generator(request))

async def _async_global_sse_generator(request: Request) -> AsyncGenerator[str, None]:
    logger.info(" ---> START RUNNING GLOBAL SSE (ALL USERS)")
    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()

    # Lắng nghe sự kiện thay đổi trên các key dạng user:*:data
    pattern = "__keyspace@0__:user:*:data"
    await pubsub.psubscribe(pattern)

    try:
        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                channel_name = message.get("channel")
                action = message.get("data")

                if isinstance(channel_name, bytes): channel_name = channel_name.decode()
                if isinstance(action, bytes): action = action.decode()

                # Chỉ xử lý khi dữ liệu thay đổi (hset)
                if action == "hset":
                    # 1. Lấy Key thật: user:22:data
                    real_key = channel_name.replace("__keyspace@0__:", "")
                    
                    # 2. Trích xuất USER_ID từ key (user:22:data -> lấy phần tử ở giữa)
                    # format: [0]user : [1]id : [2]data
                    parts = real_key.split(":")
                    user_id = parts[1] if len(parts) > 1 else None

                    # 3. Lấy dữ liệu từ Redis
                    current_data = await redis_client.hgetall(real_key)

                    # 4. Decode toàn bộ dữ liệu thô sang string
                    decoded_temp = {}
                    if current_data:
                        for k, v in current_data.items():
                            key = k.decode() if isinstance(k, bytes) else k
                            value = v.decode() if isinstance(v, bytes) else v
                            decoded_temp[key] = value

                    # 5. LỌC DỮ LIỆU: Chỉ lấy các trường cần thiết
                    # Sử dụng .get() để tránh lỗi nếu key chưa tồn tại trong Redis
                    response_payload = {
                        "user_id": user_id,
                        "start_time": decoded_temp.get("start_time"),
                        "last_time": decoded_temp.get("last_time"),
                        "img_url": decoded_temp.get("img_url"),
                        "step": decoded_temp.get("step"),
                        "lap": decoded_temp.get("lap")
                    }

                    # 6. Stream về client
                    yield f"data: {json.dumps(response_payload)}\n\n"

            await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"SSE Error: {e}")
    finally:
        try:
            await pubsub.punsubscribe(pattern)
            await pubsub.close()
        except Exception:
            pass