import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger
import json
from src.engine.engine import write_txt
from src.depend.depend import mongo_db
from src.config.config import MONGO_FLAGS_COLLECTION, MONGO_LAPS_COLLECTION
import time
from datetime import datetime
import time
from src.database.sql_model import PostgresHandler


class SetUpEvaluate:
    """
    Chỉ chịu trách nhiệm ghi flag camera vào Redis.
    """

    def __init__(self, id_run_process, redis_client=None):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client

    def set_flag_redis(self, user_id, cam_id):
        """
        Ghi flag camera nếu user đang active.
        """
        user_id = str(user_id)
        cam_id = str(cam_id)
        key_user = f"user:{user_id}:data"

        # Nếu key chưa tồn tại hoặc không active → bỏ qua
        if not self.redis_client.exists(key_user):
            return
        if self.redis_client.hget(key_user, "state") != "active":
            return

        # Ghi flag
        self.redis_client.hset(key_user, f"flag_{cam_id}", 1)


class GlobalEvaluator:
    """
    Kiểm tra lap hoàn thành và ghi PostgreSQL khi backend gửi end.
    """

    def __init__(self, id_run_process, redis_client=None, pg_handler=None):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client
        self.pg_handler = pg_handler

    def check_lap_completion(self, user_id):
        """
        Kiểm tra user hoàn thành vòng → tăng lap_number, ghi DB.
        end_time vẫn để NULL.
        """
        key_user = f"user:{user_id}:data"
        if not self.redis_client.exists(key_user):
            return
        if self.redis_client.hget(key_user, "state") != "active":
            return

        # Lấy flags
        flags = {c: int(self.redis_client.hget(key_user, f"flag_{c}")) for c in self.id_run_process}

        if all(flags.values()):
            # Tăng lap_number
            lap_number = int(self.redis_client.hget(key_user, "lap_number") or 0) + 1
            self.redis_client.hset(key_user, "lap_number", lap_number)

            # Lấy thông tin exam_id và start_time
            user_data = self.redis_client.hgetall(key_user)
            exam_id = user_data.get("exam_id")
            start_time_str = user_data.get("start_time")
            start_time = datetime.fromisoformat(start_time_str) if start_time_str else None

            # Ghi vào DB (end_time = None)
            if self.pg_handler:
                self.pg_handler.insert_or_update_lap(
                    user_id=user_id,
                    exams_id=exam_id,
                    lap_number=lap_number,
                    start_time=start_time,
                    end_time=None  # chưa có end_time
                )

            # Reset flags cho vòng tiếp theo
            pipe = self.redis_client.pipeline()
            for c in self.id_run_process:
                pipe.hset(key_user, f"flag_{c}", 0)
            pipe.execute()


    def finalize_exam(self, user_id, end_time: datetime):
        """
        Khi backend gửi end, update end_time trong DB.
        """
        key_user = f"user:{user_id}:data"
        if not self.redis_client.exists(key_user):
            return

        # Lấy lap_number, exam_id, start_time từ Redis
        user_data = self.redis_client.hgetall(key_user)
        lap_number = int(user_data.get("lap_number") or 0)
        exam_id = user_data.get("exam_id")
        start_time_str = user_data.get("start_time")
        start_time = datetime.fromisoformat(start_time_str) if start_time_str else None

        # Update end_time trong DB
        if self.pg_handler:
            self.pg_handler.insert_or_update_lap(
                user_id=user_id,
                exams_id=exam_id,
                lap_number=lap_number,
                start_time=start_time,
                end_time=end_time
            )

        # Xóa Redis key → detect/search bỏ qua user
        self.redis_client.delete(key_user)

