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
    def __init__(self, distance=None, redis_client=None, pg_handler=None):
        """
        id_run_process : list cam_id theo chu trình
        mongo_flags    : collection lưu cờ từng camera cho mỗi user
        mongo_laps     : collection lưu tổng số vòng của mỗi user
        """
        # self.id_run_process = [str(cam) for cam in id_run_process]
        # self.mongo_laps_collection = mongo_laps_collection
        # self.mongo_exams_collection = mongo_exams_collection
        self.redis_client = redis_client
        self.pg_handler = pg_handler  # placeholder nếu cần dùng PostgreSQL
        self.distance = distance  # khoảng cách giữa các camera (mét)


    def set_flag_redis(self, user_id, cam_id):
        """
        Ghi flag và thời điểm detect người ở camera cam_id.
        """
        user_id = str(user_id)
        cam_id = str(cam_id)
        key_user = f"user:{user_id}:data"
        now = datetime.now()

        self.redis_client.hset(key_user, f"flag_{cam_id}", 1)
        self.redis_client.hset(key_user, f"in_cam_{cam_id}", now.isoformat())
        self.redis_client.hset(key_user, "last_update", now.strftime("%Y-%m-%d %H:%M:%S"))
    

    
class GlobalEvaluator:
    def __init__(self, id_run_process, redis_client=None, pg_handler=None):
        self.id_run_process = [str(c) for c in id_run_process]
        self.redis_client = redis_client
        self.pg_handler = pg_handler

    def check_lap_completion(self, user_id):
        user_id = str(user_id)
        key_user = f"user:{user_id}:data"

        # Lấy toàn bộ flags
        user_data = self.redis_client.hgetall(key_user)
        flags = {
            cam: int(user_data.get(f"flag_{cam}", 0))
            for cam in self.id_run_process
        }

        # Nếu tất cả đều = 1 → hoàn thành 1 vòng
        if all(v == 1 for v in flags.values()):
            lap_number_raw = self.redis_client.hget(key_user, "lap_number")
            lap_number = int(lap_number_raw) + 1 if lap_number_raw else 1

            self.redis_client.hset(key_user, "lap_number", lap_number)

            # Tính thời gian & vận tốc
            cam_times = {}
            for cam in self.id_run_process:
                t_str = user_data.get(f"in_cam_{cam}")
                if t_str:
                    cam_times[cam] = datetime.fromisoformat(t_str)
            if len(cam_times) >= 2:
                start = min(cam_times.values())
                end = max(cam_times.values())
                duration = (end - start).total_seconds()
                distance = 100.0
                velocity = distance / duration if duration > 0 else 0
            else:
                duration = 0
                velocity = 0
                start = end = datetime.now()

            print(f"✅ User {user_id} hoàn thành vòng {lap_number}: {velocity:.2f} m/s")

            # Ghi DB
            if self.pg_handler:
                self.pg_handler.insert_lap(
                    user_id=user_id,
                    lap_number=lap_number,
                    start_time=start,
                    end_time=end,
                    lap_duration=duration,
                    velocity=velocity,
                    cam_times=cam_times,
                )

            # Reset flag
            pipe = self.redis_client.pipeline()
            for cam in self.id_run_process:
                pipe.hset(key_user, f"flag_{cam}", 0)
            pipe.execute()
