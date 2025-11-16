from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import redis
from urllib.parse import quote_plus
import os
import sys
import json
from typing import List, Optional
from src.depend.depend import BatchTrackRequest
import uvicorn
from src.config.config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.sql_model import PostgresHandler

from src.config.config import POSTGRE_USER, POSTGRE_PASSWORD, POSTGRE_HOST, POSTGRE_PORT, POSTGRE_DB
from loguru import logger


# ================== CONFIG ==================
# Kết nối Redis
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    password=REDIS_PASSWORD,
    decode_responses=True
)

try:
    redis_client.ping()
    print("✅ Kết nối Redis thành công!")
except redis.ConnectionError as e:
    print("❌ Kết nối Redis thất bại:", e)
    # In a real app, you'd want more robust error handling
    # sys.exit(1)

# Kết nối PostgreSQL
user = "labelstudio"
password = "Admin@221b"
host = "10.100.200.119"
port = 5555
database = "fitness_score"

encoded_password = quote_plus(password)
# URL kết nối PostgreSQL
DB_URL = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
pg_handler = PostgresHandler(DB_URL)

app = FastAPI()


@app.post("/track_batch")
async def track_batch(req: BatchTrackRequest):
    results = []
    logger.info(f"Received batch tracking request for {len(req.users)} users.")
    for u in req.users:
        start_user_key = f"user:{u.user_id}:data"
        try:
            if u.end_time:
                # End tracking
                data = redis_client.hgetall(start_user_key)
                if not data:
                    results.append({"user_id": u.user_id, "status": "not_found"})
                    continue

                # Decode Redis bytes → string
                redis_client.hset(start_user_key, "state", "ended")
                logger.info(f"Data from Redis for user {u.user_id}: {data}")
                exam_id = int(data.get("exam_id"))
                step = int(data.get("step"))
                lap = int(data.get("lap_number"))
                start_time = data.get("start_time")
                end_time = u.end_time   # duy nhất lấy từ request

                # Update trạng thái
                logger.info(f"User {u.user_id} ended tracking: exam_id={exam_id}, step={step}, lap={lap}, start_time={start_time}, end_time={end_time}")
                # Ghi DB
                pg_handler.insert_or_update_lap(
                    user_id=int(u.user_id),
                    exam_id=exam_id,
                    step=step,
                    lap_number=lap,
                    start_time=start_time,
                    end_time=end_time
                )

                # Xoá key nếu cần
                redis_client.delete(start_user_key)

                results.append({"user_id": u.user_id, "status": "ended"})
                continue

            if u.exam_id and u.start_time:
                # Start tracking
                redis_client.hset(start_user_key, mapping={
                    "state": "active",
                    "exam_id": u.exam_id,
                    "step": u.step if u.step is not None else "",
                    "start_time": u.start_time,
                    "lap": 0,
                    "flag_1": 0, "flag_2": 0, "flag_3": 0, "flag_4": 0,
                    "last_cam": -1
                })
                results.append({"user_id": u.user_id, "status": "started"})
                continue

            results.append({"user_id": u.user_id, "status": "no_action"})
        except Exception as e:
            results.append({"user_id": u.user_id, "status": "error", "detail": str(e)})

    return {"results": results}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)