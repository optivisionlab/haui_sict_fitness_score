import numpy as np
from typing import Union


class SetUpEvaluate():
    # khởi tạo chu trình
    def __init__(self, id_run_process: Union[list, np.ndarray], user_info: Union[dict], mean_velocity=[8, 12]):
        """
        Khởi tạo các biến truyền vào
        Input:
            - id_run_process: Chu trình setup camera
            - user_info: Thông tin dạng dict gồm tên và thời gian chạy, ...
            - mean_velocity: vận tốc chạy trung bình của người bình thường
        TODO:
            - thuật toán tính điểm theo vận tốc, hoặc một cách gì đó
        """
        self.id_run_process = id_run_process
        self.user_info = user_info
        self.mean_velocity = mean_velocity
    
    # Lấy chu trình 
    def __get_process(self):
        if isinstance(self.id_run_process, list):
            self.id_run_process = np.array(self.id_run_process)

        return self.id_run_process
    
    # validate chu trình của 1 user
    def __validate_process(self, **kwargs):
        """
        Hàm validate chu trình
        Input:
            - cam_ids: list/array chứa id camera
            - time_accesses: list/array chứa thời gian tương ứng
            HOẶC
            - cam_time_dict: dict {cam_id: time_access}
        """
        cam_ids = None
        time_accesses = None

        # Nếu input là 2 mảng riêng
        if 'cam_ids' in kwargs and 'time_accesses' in kwargs:
            cam_ids = kwargs['cam_ids']
            time_accesses = kwargs['time_accesses']
        
        # Nếu input là dictionary
        elif 'cam_time_dict' in kwargs:
            cam_time_dict = kwargs['cam_time_dict']
            cam_ids = list(cam_time_dict.keys())
            time_accesses = list(cam_time_dict.values())
        else:
            raise ValueError("Input không hợp lệ. Cần truyền cam_ids + time_accesses hoặc cam_time_dict.")

        # Validate tập ID
        if set(cam_ids) != set(self.id_run_process):
            return False

        original_cam_ids = list(cam_ids)

        # Validate từng phần tử
        for cam_id, time_access in zip(cam_ids, time_accesses):
            if not isinstance(cam_id, (int, str)):
                return False
            if not isinstance(time_access, (int, float)):
                return False

        sort_time = sorted(zip(cam_ids, time_accesses), key=lambda x: x[1])
        sorted_cam_ids, _ = zip(*sort_time)
        
        return list(sorted_cam_ids) == original_cam_ids
            
    
    def __eval(self, **kwargs):
        """
        Đánh giá thời gian một người đi qua toàn bộ chu trình.
        Input giống __validate_process:
            - cam_ids + time_accesses
            HOẶC
            - cam_time_dict
        Output:
            - total_time: tổng thời gian từ cam đầu đến cam cuối
            - time_details: dict {("camX", "camY"): delta_time}
        """
        cam_ids = None
        time_accesses = None

        # Lấy dữ liệu input
        if 'cam_ids' in kwargs and 'time_accesses' in kwargs:
            cam_ids = kwargs['cam_ids']
            time_accesses = kwargs['time_accesses']
        elif 'cam_time_dict' in kwargs:
            cam_time_dict = kwargs['cam_time_dict']
            cam_ids = list(cam_time_dict.keys())
            time_accesses = list(cam_time_dict.values())
        else:
            raise ValueError("Input không hợp lệ. Cần truyền cam_ids + time_accesses hoặc cam_time_dict.")

        # Chuyển thành dict để dễ lookup
        cam_time_map = dict(zip(cam_ids, time_accesses))

        # Duyệt theo đúng thứ tự chu trình
        ordered_cams = list(self.id_run_process)

        # Tính thời gian giữa các camera liên tiếp
        time_details = {}
        total_time = 0
        for i in range(len(ordered_cams) - 1):
            cam_a = ordered_cams[i]
            cam_b = ordered_cams[i + 1]
            
            if cam_a not in cam_time_map or cam_b not in cam_time_map:
                raise ValueError(f"Thiếu dữ liệu thời gian cho {cam_a} hoặc {cam_b}.")

            delta_time = cam_time_map[cam_b] - cam_time_map[cam_a]
            time_details[(cam_a, cam_b)] = delta_time
            total_time += delta_time

        return total_time, time_details

