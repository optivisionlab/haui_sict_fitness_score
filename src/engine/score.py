import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger
import json
from src.engine.engine import write_txt


class SetUpEvaluate():
    def __init__(self, id_run_process: Union[list, np.ndarray], mean_velocity=[8, 12], test_mode=False, server_file="server.json"):
        """
        Input:
            - id_run_process: Chu trình setup camera (list hoặc array)
            - mean_velocity: khoảng vận tốc chạy trung bình
        """
        self.id_run_process = np.array(id_run_process) if isinstance(id_run_process, list) else id_run_process
        self.mean_velocity = mean_velocity

        # Lưu trạng thái cho từng user
        self.laps = defaultdict(int)                         # laps[user_id]
        self.progress_idx = defaultdict(lambda: -1)          # user đang ở bước thứ mấy trong chu trình
        self.last_timestamp = defaultdict(lambda: None)      # lưu thời gian lần cuối update
        self.last_cam = defaultdict(lambda: None)  # lưu camera cuối cùng
        self.start_cam = defaultdict(lambda: None)  # lưu camera bắt đầu
        self.direction = defaultdict(lambda: None)  # hướng di chuyển (tăng hay giảm cam_id)
        self.test_mode = test_mode
        self.server_file = server_file
        # sử dụng để demo, cứ 4 cờ bật là True
        self.cam_flags = defaultdict(lambda: {int(cam): False for cam in self.id_run_process})
        
        if self.test_mode:
            try:
                with open(self.server_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.server_data = data.get("users", {})
                    self.laps.update(data.get("laps", {}))
                    last_cam = data.get("last_cam", {})
                    if isinstance(last_cam, dict):
                        self.last_cam.update(last_cam)
            except (FileNotFoundError, json.JSONDecodeError):
                self.server_data = {}
                self._save_server()
        
        
    def _save_server(self):
        if not self.test_mode:
            return
        data = {
            "users": self.server_data,
            "laps": dict(self.laps),
            "last_cam": dict(self.last_cam),
        }
        with open(self.server_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            

    def update_flags(self, user_id, cam_id, timestamp=None):
        user_id = str(user_id)
        cam_id = str(cam_id)

        # Nếu user chưa có trong server thì tạo mới
        if user_id not in self.server_data:
            self.server_data[user_id] = {str(cam): False for cam in self.id_run_process}
            self.laps[user_id] = 0

        # ✅ bật cờ cho cam_id hiện tại
        self.server_data[user_id][cam_id] = True

        # Nếu tất cả cam đều True → hoàn thành 1 vòng
        if all(self.server_data[user_id].values()):
            self.laps[user_id] += 1
            logger.info(f"✅ User {user_id} hoàn thành vòng {self.laps[user_id]}")

            # Reset cờ cho vòng tiếp theo
            self.server_data[user_id] = {str(cam): False for cam in self.id_run_process}

        self._save_server()
     
    # def update_flags(self, user_id, cam_id, timestamp=None):
    #     user_id = str(user_id)
    #     cam_id = str(cam_id)

    #     # Nếu user chưa có trong server thì tạo mới
    #     if user_id not in self.server_data:
    #         self.server_data[user_id] = {str(cam): False for cam in self.id_run_process}
    #         self.last_cam[user_id] = None
    #         self.laps[user_id] = 0

    #     # Lấy cam trước đó
    #     prev_cam = self.last_cam.get(user_id, None)

    #     # Nếu lần đầu → cho phép bất kỳ cam
    #     if prev_cam is None:
    #         self.server_data[user_id][cam_id] = True
    #         self.last_cam[user_id] = cam_id
    #     else:
    #         # Tìm index trong id_run_process
    #         if cam_id == prev_cam:
    #             return

    #         cams = list(map(str, self.id_run_process))
    #         prev_idx = cams.index(prev_cam)
    #         allowed_next = {cams[(prev_idx - 1) % len(cams)], cams[(prev_idx + 1) % len(cams)]}

    #         if cam_id in allowed_next:
    #             # ✅ Hợp lệ → bật cờ
    #             self.server_data[user_id][cam_id] = True
    #             self.last_cam[user_id] = cam_id
    #         else:
    #             # Sai thứ tự → reset flags & last_cam (logic giữ nguyên)
    #             self.server_data[user_id] = {str(cam): False for cam in self.id_run_process}
    #             self.last_cam[user_id] = None
    #             logger.info(f"⚠️ User {user_id} đi sai thứ tự, reset vòng")

    #     # Nếu tất cả True → cộng lap
    #     if all(self.server_data[user_id].values()):
    #         self.laps[user_id] += 1
    #         logger.info(f"✅ User {user_id} hoàn thành vòng {self.laps[user_id]}")

    #         # Reset cờ
    #         self.server_data[user_id] = {str(cam): False for cam in self.id_run_process}
    #         self.last_cam[user_id] = None

    #     self._save_server()

        
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


    def get_status(self, user_id):
        if self.test_mode:
            return {
            "laps": self.laps[user_id],
            "flags": self.cam_flags[user_id],
            "progress_idx": self.progress_idx[user_id],
            "last_timestamp": self.last_timestamp[user_id],
            "start_cam": self.start_cam[user_id],
            "direction": self.direction[user_id]
        }
            
        return {
            "laps": self.laps[user_id],
            "progress_idx": self.progress_idx[user_id],
            "last_timestamp": self.last_timestamp[user_id],
            "start_cam": self.start_cam[user_id],
            "direction": self.direction[user_id]
        }
    

class GlobalEvaluator:
    """
    Giữ 1 evaluator duy nhất cho toàn bộ hệ thống.
    Các tracker sẽ gọi process_from_tracker để cập nhật.
    """
    def __init__(self, id_run_process, mean_velocity=[8, 12], test_mode=False):
        self.evaluator = SetUpEvaluate(id_run_process, mean_velocity, test_mode=test_mode)

    def process_from_tracker(self, detections, cam_id, timestamp=None):
        """
        detections: list user_id đã detect sau API
        cam_id: ID camera
        """
        for user_id in detections:
            # self.evaluator.update_random_direction(user_id, cam_id, timestamp)
            self.evaluator.update_flags(user_id, cam_id, timestamp)

    def get_status(self, user_id):
        return self.evaluator.get_status(user_id)

    def get_all_status(self):
        return {uid: self.evaluator.get_status(uid) for uid in self.evaluator.laps.keys()}

