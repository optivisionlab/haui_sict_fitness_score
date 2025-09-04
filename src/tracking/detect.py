import random
from collections import defaultdict

# Giả sử đã import sẵn
from src.engine.score import SetUpEvaluate
from src.search.curl_api_search import send_tracking_to_api


class SimpleTracker:
    def __init__(self, detection_model, id_run_process, cam_id, mean_velocity=[8,12]):
        """
        detection_model: YOLO model để detect người
        id_run_process: chu trình camera (ví dụ [1,2,3])
        cam_id: camera hiện tại
        """
        self.detection_model = detection_model
        self.cam_id = cam_id
        self.evaluator = SetUpEvaluate(id_run_process, mean_velocity)
        self.id_to_name = {}   # mapping API id -> name
        # self.user_ids = []  # danh sách user_id đã detect

    def process_frame(self, frame):
        """
        Xử lý 1 frame: detect người, random id, gửi API, update laps.
        """
        # ----- Detection YOLO -----
        detection_results = self.detection_model(frame, conf=0.5, iou=0.5, verbose=True)[0]

        ids, xyxy_boxes, current_user_ids = [], [], []
        for box in detection_results.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls == 0:  # person
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                xyxy_boxes.append([x1, y1, x2, y2])
                ids.append(random.randint(1, 100))  # random id tạm

        annotated_frame = frame.copy()

        if ids:
            try:
                # ----- Gửi API -----
                response = send_tracking_to_api(ids, xyxy_boxes, frame)
                if response and response.status_code == 200:
                    api_data = response.json().get("data", [])
                    for entry in api_data:
                        uid = entry.get("id")            # ID thật từ API
                        infor = entry.get("infor", {})
                        metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                        name = metadata.get("name", "Unknown")
                        user_id = metadata.get("id", "Unknown")  # Giả sử ID từ API là user_id
                        # lưu tên
                        self.id_to_name[user_id] = name

                        # update laps cho user này
                        self.evaluator.update(user_id=user_id, cam_id=self.cam_id)

                else:
                    print(f"API trả lỗi: {response.status_code}")
            except Exception as e:
                print(f"Lỗi khi gửi API: {e}")
                # self.evaluator.update(user_id=1, cam_id=self.cam_id)

    def get_user_status(self, user_id):
        """Lấy số vòng & trạng thái camera của 1 user"""
        return self.evaluator.get_status(user_id)
