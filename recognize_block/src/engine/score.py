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
from src.depend.depend import minio_client


class SetUpEvaluate:
    """
    Chỉ chịu trách nhiệm ghi flag camera vào Redis.
    """

    def __init__(self, id_run_process, redis_client=None, pg_handler=None, test_mode=False):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client
        self.pg_handler = pg_handler
        self.test_mode = test_mode

    def set_flag_redis(self, user_id, cam_id, copy_frame=None, timestamp=None):
        """
        Ghi flag camera nếu user đang active.
        """
        user_id = str(user_id)
        cam_id = str(cam_id)
        timestamp=timestamp
        key_user = f"user:{user_id}:data"
        if self.test_mode and not self.redis_client.exists(key_user):
            logger.warning(f"[TEST_MODE] Init redis key for user {user_id}")
            self.redis_client.hset(key_user, mapping={
                "state": "active",
                "exam_id": -1,
                "step": 0,
                "lap": 0,
                "start_time": timestamp,
                "last_cam": "",
                "flag_1": 0,
                "flag_2": 0,
                "flag_3": 0,
                "flag_4": 0,
            })
        # Nếu key chưa tồn tại hoặc không active → bỏ qua
        if not self.test_mode:
            if not self.redis_client.exists(key_user):
                return
            if self.redis_client.hget(key_user, "state") != "active":
                return

        # Ghi flag
        last_cam = self.redis_client.hget(key_user, "last_cam")
        if str(last_cam) == cam_id:
            return
        
        self.redis_client.hset(key_user, f"flag_{cam_id}", 1)
        self.redis_client.hset(key_user, "last_cam", cam_id)
        self.redis_client.hset(key_user, f"last_time", timestamp) 
        img_url = minio_client.push_data(image=copy_frame, destination_file=f"{timestamp}/{user_id}.jpg")
        logger.info(f"Image URL for user {user_id}: {img_url}")
        self.redis_client.hset(key_user, f"img_url", img_url) 
        # self.pg_handler.insert_postgre(
        #     user_id=user_id,
        #     exam_id=self.redis_client.hget(key_user, "exam_id"),
        #     step=int(self.redis_client.hget(key_user, "step") or 0),
        #     lap=int(self.redis_client.hget(key_user, "lap") or 0),
        #     start_time=self.redis_client.hget(key_user, "start_time"),
        #     flag1=int(self.redis_client.hget(key_user, "flag_1") or 0),
        #     flag2=int(self.redis_client.hget(key_user, "flag_2") or 0),
        #     flag3=int(self.redis_client.hget(key_user, "flag_3") or 0),
        #     flag4=int(self.redis_client.hget(key_user, "flag_4") or 0),
        #     url=img_url
        # )
        logger.error(f"User {user_id} - set flag cam {cam_id}")


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

        if str(state) == "active":
        # Lấy flags
            logger.error(f"Checking lap for user {user_id}")
            flags = {c: int(self.redis_client.hget(key_user, f"flag_{c}")) for c in self.id_run_process}

            if all(flags.values()):
                # Tăng lap_number
                lap_number = int(self.redis_client.hget(key_user, "lap") or 0) + 1
                self.redis_client.hset(key_user, "lap", lap_number)
                for c in self.id_run_process:
                    self.redis_client.hset(key_user, f"flag_{c}", 0)
                logger.debug(f"User {user_id} hoàn thành vòng {lap_number} → reset flags")


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
