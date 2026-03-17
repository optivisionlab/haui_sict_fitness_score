from typing import AsyncGenerator
import json
import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.core.database import get_async_redis
import hashlib
import time 


logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/events/global")
async def global_events(request: Request):
    return StreamingResponse(_async_global_sse_generator(request))

async def _async_global_sse_generator(request: Request) -> AsyncGenerator[str, None]:
    logger.info(" ---> START RUNNING GLOBAL SSE (SMART DEDUPLICATION)")
    redis_client = get_async_redis()
    pubsub = redis_client.pubsub()

    pattern = "__keyspace@0__:user:*:data"
    await pubsub.psubscribe(pattern)

    # Dictionary lưu hash của lần gửi cuối cùng
    last_sent_hash = {}

    try:
        while True:
            # 1. Kiểm tra kết nối
            if await request.is_disconnected():
                logger.info("Client disconnected")
                break
            start_time = time.time()
            # 2. Nhận tin nhắn từ Redis
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                channel_name = message.get("channel")
                action = message.get("data")

                # Decode bytes sang string nếu cần
                if isinstance(channel_name, bytes): channel_name = channel_name.decode()
                if isinstance(action, bytes): action = action.decode()

                # 3. Chỉ xử lý sự kiện 'hset'
                if action == "hset":
                    # Parse User ID từ channel: __keyspace@0__:user:13:data
                    real_key = channel_name.replace("__keyspace@0__:", "")
                    parts = real_key.split(":")
                    user_id = parts[1] if len(parts) > 1 else None

                    if not user_id: 
                        continue

                    # Lấy toàn bộ dữ liệu hiện tại từ Redis
                    current_data = await redis_client.hgetall(real_key)
                    
                    decoded_temp = {}
                    if current_data:
                        for k, v in current_data.items():
                            key = k.decode() if isinstance(k, bytes) else k
                            value = v.decode() if isinstance(v, bytes) else v
                            decoded_temp[key] = value
                    response_payload = {
                        "user_id": user_id,
                        "start_time": decoded_temp.get("start_time"),
                        "last_time": decoded_temp.get("last_time"),
                        "last_cam": decoded_temp.get("last_cam"),
                        "img_url": decoded_temp.get("img_url"),
                        "step": decoded_temp.get("step"),
                        "lap": decoded_temp.get("lap")
                    }
                    compare_payload = {
                        "user_id": user_id,
                        "last_time": decoded_temp.get("last_time"),
                        "last_cam": decoded_temp.get("last_cam"),
                        "step": decoded_temp.get("step"),
                        "lap": decoded_temp.get("lap")
                    }

                    compare_str = json.dumps(compare_payload, sort_keys=True)
                    current_hash = hashlib.md5(compare_str.encode()).hexdigest()

                    if last_sent_hash.get(user_id) == current_hash:
                        continue
                    end_time = time.time()
                    total_time = end_time - start_time
                    with open("ghichu.txt", "w") as f:
                        f.write(f"{total_time}\n")
    
                    last_sent_hash[user_id] = current_hash
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