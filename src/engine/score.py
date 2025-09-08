import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger
import json
from src.engine.engine import write_txt


class SetUpEvaluate():
    def __init__(self, id_run_process: Union[list, np.ndarray], mean_velocity=[8, 12]):
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


    def update(self, user_id, cam_id, timestamp=None):
        if cam_id not in self.id_run_process:
            raise ValueError(f"Camera {cam_id} không thuộc chu trình.")

        prev_idx = self.progress_idx[user_id]
        expected_next = 0 if prev_idx == -1 else (prev_idx + 1) % len(self.id_run_process)
        logger.info(f"user {user_id} prev_idx={prev_idx}, expected_next={expected_next}, cam_id={cam_id}")

        # Phần này debug việc search ra kết quả liên tục ở 1 cam
        if self.last_cam[user_id] == cam_id:
            logger.debug(f"User {user_id} bị trùng cam {cam_id} -> bỏ qua update")
            return

        if cam_id == self.id_run_process[expected_next]:
            # Đi đúng thứ tự
            if expected_next == 0 and prev_idx == len(self.id_run_process) - 1:
                # Chỉ cộng vòng khi từ cam cuối quay lại cam đầu
                self.laps[user_id] += 1
                logger.info(f"User {user_id} hoàn thành vòng {self.laps[user_id]}")
                write_txt('results.txt', f"User {user_id} hoàn thành vòng {self.laps[user_id]}")

            self.progress_idx[user_id] = expected_next
            self.last_timestamp[user_id] = timestamp
            self.last_cam[user_id] = cam_id

        else:
            # Sai thứ tự thì reset
            self.progress_idx[user_id] = -1
            self.last_cam[user_id] = cam_id
            if cam_id == self.id_run_process[0]:
                self.progress_idx[user_id] = 0
                self.last_timestamp[user_id] = timestamp
                logger.info(f"User {user_id} restart lại từ cam đầu ({cam_id})")


    def update_random_direction(self, user_id, cam_id, timestamp=None):
        # cam_id phải thuộc chu trình
        if cam_id not in self.id_run_process:
            raise ValueError(f"Camera {cam_id} không thuộc chu trình.")

        prev_idx = self.progress_idx[user_id]
        start_cam = self.start_cam[user_id]
        direction = self.direction[user_id]

        logger.info(f"[User {user_id}] prev_idx={prev_idx}, cam_id={cam_id}, start_cam={start_cam}, direction={direction}")

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
            logger.info(f"[User {user_id}] Khởi động lại tại cam {cam_id}")
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
        expected_cam = seq[expected_idx]

        if cam_id == expected_cam:
            # đi đúng thứ tự
            self.progress_idx[user_id] = expected_idx
            self.last_timestamp[user_id] = timestamp
            self.last_cam[user_id] = cam_id

            # nếu quay lại start (expected_idx == 0) -> hoàn thành vòng
            if expected_idx == 0:
                self.laps[user_id] += 1
                logger.info(f"User {user_id} hoàn thành vòng {self.laps[user_id]}")
                # cho phép đổi hướng ở vòng tiếp theo
                self.direction[user_id] = None
            return

        # nếu đến đây -> đi sai thứ tự => reset sạch để user có thể restart
        self.progress_idx[user_id] = -1
        self.direction[user_id] = None
        self.last_cam[user_id] = None
        logger.warning(f"[User {user_id}] Sai thứ tự tại cam {cam_id} -> reset")



    def get_status(self, user_id):
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
    def __init__(self, id_run_process, mean_velocity=[8, 12]):
        self.evaluator = SetUpEvaluate(id_run_process, mean_velocity)

    def process_from_tracker(self, detections, cam_id, timestamp=None):
        """
        detections: list user_id đã detect sau API
        cam_id: ID camera
        """
        for user_id in detections:
            self.evaluator.update_random_direction(user_id, cam_id, timestamp)

    def get_status(self, user_id):
        return self.evaluator.get_status(user_id)

    def get_all_status(self):
        return {uid: self.evaluator.get_status(uid) for uid in self.evaluator.laps.keys()}

