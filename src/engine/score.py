import numpy as np
from typing import Union
from collections import defaultdict
from loguru import logger


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

    def update(self, user_id, cam_id, timestamp=None):
        """
        Cập nhật khi 1 người xuất hiện ở camera
        Input:
            - user_id: ID của người
            - cam_id: ID camera
            - timestamp: thời gian (nếu cần)
        """
        if cam_id not in self.id_run_process:
            raise ValueError(f"Camera {cam_id} không thuộc chu trình.")

        expected_next = 0 if self.progress_idx[user_id] == -1 else (self.progress_idx[user_id] + 1) % len(self.id_run_process)

        if cam_id == self.id_run_process[expected_next]:
            # Đi đúng trình tự
            self.progress_idx[user_id] = expected_next
            self.last_timestamp[user_id] = timestamp

            if self.progress_idx[user_id] == 0:  # quay lại điểm đầu -> hoàn thành 1 vòng
                self.laps[user_id] += 1
                logger.info(f"✅ User {user_id} hoàn thành vòng {self.laps[user_id]}")

        else:
            # Nếu đi sai thứ tự thì reset progress
            self.progress_idx[user_id] = -1

    def get_status(self, user_id):
        return {
            "laps": self.laps[user_id],
            "progress_idx": self.progress_idx[user_id],
            "last_timestamp": self.last_timestamp[user_id]
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
            self.evaluator.update(user_id, cam_id, timestamp)

    def get_status(self, user_id):
        return self.evaluator.get_status(user_id)

    def get_all_status(self):
        return {uid: self.evaluator.get_status(uid) for uid in self.evaluator.laps.keys()}

