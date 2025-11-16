import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger
import json
from src.engine.engine import write_txt
# from src.depend.depend import mongo_db
# from src.config.config import MONGO_FLAGS_COLLECTION, MONGO_LAPS_COLLECTION
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
        last_cam = self.redis_client.hget(key_user, "last_cam")
        if last_cam == cam_id:
            return

        self.redis_client.hset(key_user, f"flag_{cam_id}", 1)
        self.redis_client.hset(key_user, "last_cam", cam_id)


    def check_lap_1_user(self, user_id):
        """
        Kiểm tra user hoàn thành vòng → tăng lap_number.
        Không ghi DB.
        """
        key_user = f"user:{user_id}:data"
        lap_lock = f"user:{user_id}:lap_lock"
        locked = self.redis_client.set(lap_lock, 1, nx=True, ex=2)

        if not self.redis_client.exists(key_user):
            return
        
        if not locked:
            return  # đang có process khác xử lý user này
        
        state = self.redis_client.hget(key_user, "state")

        if state == "active":
        # Lấy flags
            flags = {c: int(self.redis_client.hget(key_user, f"flag_{c}")) for c in self.id_run_process}

            if all(flags.values()):
                # Tăng lap_number
                lap_number = int(self.redis_client.hget(key_user, "lap_number") or 0) + 1
                self.redis_client.hset(key_user, "lap_number", lap_number)


class GlobalEvaluator:
    """
    Kiểm tra lap hoàn thành và ghi PostgreSQL khi backend gửi end.
    """

    def __init__(self, id_run_process, redis_client=None, pg_handler=None):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client
        self.pg_handler = pg_handler

    def check_lap_1_user(self, user_id):
        """
        Kiểm tra user hoàn thành vòng → tăng lap_number, ghi DB.
        end_time vẫn để NULL.
        """
        key_user = f"user:{user_id}:data"
        lap_lock = f"user:{user_id}:lap_lock"
        locked = self.redis.set(lap_lock, 1, nx=True, ex=2)

        if not self.redis_client.exists(key_user):
            return
        
        if not locked:
            return  # đang có process khác xử lý user này
        
        state = self.redis_client.hget(key_user, "state")

        if state == "active":
        # Lấy flags
            flags = {c: int(self.redis_client.hget(key_user, f"flag_{c}")) for c in self.id_run_process}

            if all(flags.values()):
                # Tăng lap_number
                lap_number = int(self.redis_client.hget(key_user, "lap_number") or 0) + 1
