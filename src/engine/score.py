import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger
import json
from src.engine.engine import write_txt
from src.depend.depend import mongo_db
import time
from datetime import datetime
import time


class SetUpEvaluate:
    def __init__(self, id_run_process, mongo_flags="flags_db", mongo_laps="laps_db"):
        """
        id_run_process : list cam_id theo chu trình
        mongo_flags    : collection lưu cờ từng camera cho mỗi user
        mongo_laps     : collection lưu tổng số vòng của mỗi user
        """
        self.id_run_process = [str(cam) for cam in id_run_process]
        self.mongo_flags = mongo_flags
        self.mongo_laps = mongo_laps


    def update_flags(self, user_id, cam_id):
        """
        Bật cờ cho 1 camera của user.
        - Nếu tất cả cờ đều True → +1 vòng trong collection laps_db
        """
        user_id = str(user_id)
        cam_id = str(cam_id)

        # --- Bật cờ duy nhất cam_id bằng $set ---
        mongo_db.collection(self.mongo_flags).update_one(
            {"_id": user_id},
            {
                "$set": {
                    f"flags.{cam_id}": True,
                    "timestamp": time.time()
                },
                # bảo đảm document luôn có đầy đủ key flags.<cam> = False khi mới tạo
                "$setOnInsert": {
                    **{f"flags.{c}": False for c in self.id_run_process if c != cam_id},
                    "created_at": time.time()
                }
            },
            upsert=True
        )

        # --- Đếm số cờ hiện tại ---
        doc = mongo_db.collection(self.mongo_flags).find_one({"_id": user_id})
        if not doc:
            return

        flags = doc.get("flags", {})
        # kiểm tra tất cả camera đã True
        if all(flags.get(c) for c in self.id_run_process):
            # +1 vòng và reset cờ
            logger.info(f"✅ User {user_id} hoàn thành 1 vòng")
            mongo_db.collection(self.mongo_laps).update_one(
                {"_id": user_id},
                {"$inc": {"laps": 1}, "$set": {"updated_at": time.time()}},
                upsert=True
            )
            # reset toàn bộ flags về False
            mongo_db.collection(self.mongo_flags).update_one(
                {"_id": user_id},
                {"$set": {f"flags.{c}": False for c in self.id_run_process}}
            )


    def get_status(self, user_id):
        user_id = str(user_id)
        flags_doc = mongo_db.find_one(self.mongo_flags, {"_id": user_id}) or {}
        laps_doc  = mongo_db.find_one(self.mongo_laps,  {"_id": user_id}) or {}
        return {
            "laps":  laps_doc.get("laps", 0),
            "flags": flags_doc.get("flags", {cam: False for cam in self.id_run_process}),
            "timestamp": laps_doc.get("timestamp")
        }

        
    def update_random_direction(self, user_id, cam_id, timestamp=None):
        # cam_id phải thuộc chu trình
        if cam_id not in self.id_run_process:
            raise ValueError(f"Camera {cam_id} không thuộc chu trình.")

        prev_idx = self.progress_idx[user_id]
        start_cam = self.start_cam[user_id]
        direction = self.direction[user_id]

        logger.info(f"[User {user_id}] prev_idx={prev_idx}, cam_id={cam_id}, start_cam={start_cam}, direction={direction}")
        write_txt('logs.txt', f"[User {user_id}] prev_idx={prev_idx}, cam_id={cam_id}, start_cam={start_cam}, direction={direction}")

        # nếu user đã có progress và detect trùng cam liên tiếp -> bỏ qua (spam)
        if prev_idx != -1 and self.last_cam[user_id] == cam_id:
            logger.debug(f"[User {user_id}] Trùng cam {cam_id} -> bỏ qua")
            return

        cam_list = list(self.id_run_process)
        N = len(cam_list)

        # ---------- 1) reset / khởi động mới ----------
        if prev_idx == -1:
            # user bắt đầu ở cam này
            self.start_cam[user_id] = cam_id
            self.progress_idx[user_id] = 0
            self.last_cam[user_id] = cam_id
            self.last_timestamp[user_id] = timestamp
            self.direction[user_id] = None
            logger.info(f"[User {user_id}] Khởi động bắt đầu tại cam {cam_id}")
            return

        # index của cam start trong cam_list
        start_idx = cam_list.index(self.start_cam[user_id])

        # ---------- 2) nếu chưa biết hướng -> xác định ở bước 2 ----------
        if direction is None:
            cw_next  = cam_list[(start_idx + 1) % N]
            ccw_next = cam_list[(start_idx - 1) % N]

            if cam_id == cw_next:
                self.direction[user_id] = "cw"
                self.progress_idx[user_id] = 1
                self.last_cam[user_id] = cam_id
                self.last_timestamp[user_id] = timestamp
                logger.info(f"[User {user_id}] Chọn hướng cw (bước 2)")
                return
            elif cam_id == ccw_next:
                self.direction[user_id] = "ccw"
                self.progress_idx[user_id] = 1
                self.last_cam[user_id] = cam_id
                self.last_timestamp[user_id] = timestamp
                logger.info(f"[User {user_id}] Chọn hướng ccw (bước 2)")
                return
            else:
                # không đi sang 2 cam kế tiếp từ start -> coi là sai và reset
                self.progress_idx[user_id] = -1
                self.last_cam[user_id] = None
                logger.warning(f"[User {user_id}] Sai hướng ngay bước 2 -> reset")
                return

        # ---------- 3) nếu đã biết hướng -> build sequence theo start+direction ----------
        if self.direction[user_id] == "cw":
            seq = [cam_list[(start_idx + i) % N] for i in range(N)]
        else:  # ccw
            seq = [cam_list[(start_idx - i) % N] for i in range(N)]

        # progress_idx là số bước đã đi kể từ start (0..N-1)
        expected_idx = (prev_idx + 1) % N
        expected_cam = int(seq[expected_idx])
        cam_id = int(cam_id)
        logger.info(f"[User {user_id}] direction={self.direction[user_id]}, expected_cam={expected_cam}, cam_id={cam_id}")
        if cam_id == expected_cam:
            # đi đúng thứ tự
            self.progress_idx[user_id] = expected_idx
            self.last_timestamp[user_id] = timestamp
            self.last_cam[user_id] = cam_id
            # nếu quay lại start (expected_idx == 0) -> hoàn thành vòng
          # 🔹 Test mode: coi khi đi hết 1 vòng (expected_idx == N-1) là hoàn thành
            if self.test_mode and expected_idx == N - 1:
                logger.info(f"prev_idx={prev_idx}, N-1={N-1}, expected_idx={expected_idx}")
                self.laps[user_id] += 1
                logger.info(f"[TEST MODE] User {user_id} hoàn thành vòng {self.laps[user_id]}")
                # write_txt('results.txt', f"[TEST MODE] User {user_id} hoàn thành vòng {self.laps[user_id]}")

                self.direction[user_id] = None
                self.progress_idx[user_id] = -1  # reset để chạy vòng mới
                return

            # 🔹 Normal mode: chỉ tính vòng khi quay lại start
            if not self.test_mode and expected_idx == 0:
                self.laps[user_id] += 1
                logger.info(f"User {user_id} hoàn thành vòng {self.laps[user_id]}")
                # write_txt('results.txt', f"[TEST MODE] User {user_id} hoàn thành vòng {self.laps[user_id]}")
                self.direction[user_id] = None
                return
            return

        # nếu đến đây -> đi sai thứ tự => reset sạch để user có thể restart
        self.progress_idx[user_id] = -1
        self.direction[user_id] = None
        self.last_cam[user_id] = None
        logger.warning(f"[User {user_id}] Sai thứ tự tại cam {cam_id} -> reset")
    

class GlobalEvaluator:
    """
    Giữ 1 evaluator duy nhất cho toàn bộ hệ thống.
    Các tracker sẽ gọi process_from_tracker để cập nhật.
    """
    def __init__(self, id_run_process, mean_velocity=[8, 12]):
        self.evaluator = SetUpEvaluate(id_run_process, mean_velocity)

    def process_from_tracker(self, detections, cam_id):
        """
        detections: list user_id đã detect sau API
        cam_id: ID camera
        """
        for user_id in detections:
            self.evaluator.update_flags(user_id, cam_id)

    def get_status(self, user_id):
        return self.evaluator.get_status(user_id)

    def get_all_status(self):
        return {uid: self.evaluator.get_status(uid) for uid in self.evaluator.laps.keys()}

