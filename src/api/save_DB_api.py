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
# from src.config.config import POSTGRE_USER, POSTGRE_PASSWORD, POSTGRE_HOST, POSTGRE_PORT, POSTGRE_DB

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


app = FastAPI()


@app.post("/track_batch")
async def track_batch(req: BatchTrackRequest):
    results = []
    for u in req.users:
        user_key = f"user:{u.user_id}:data"
        try:
            if u.end_time:
                # End tracking
                redis_client.delete(user_key)
                results.append({"user_id": u.user_id, "status": "ended"})
                continue

            if u.exam_id and u.start_time:
                # Start tracking
                now = u.start_time.isoformat() if u.start_time else datetime.now().isoformat()
                redis_client.hset(user_key, mapping={
                    "state": "active",
                    "exam_id": u.exam_id,
                    "session_start_time": now,
                    "lap_number": 0,
                    "flag_1": 0, "flag_2": 0, "flag_3": 0, "flag_4": 0,
                })
                results.append({"user_id": u.user_id, "status": "started"})
                continue

            results.append({"user_id": u.user_id, "status": "no_action"})
        except Exception as e:
            results.append({"user_id": u.user_id, "status": "error", "detail": str(e)})

    return {"results": results}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)