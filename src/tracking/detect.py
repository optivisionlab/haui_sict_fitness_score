import random
from collections import defaultdict

# Giả sử đã import sẵn
from src.engine.score import SetUpEvaluate
from src.search.curl_api_search import send_tracking_to_api
from ultralytics import YOLO
from loguru import logger

class SimpleTracker:
    def __init__(self, detection_model, cam_id, global_evaluator):
        """
        detection_model: YOLO model để detect người
        cam_id: camera hiện tại
        global_evaluator: đối tượng GlobalEvaluator (chung cho mọi tracker)
        """
        # ở đây KHÔNG load YOLO lại nữa, chỉ dùng model truyền vào
        self.detection_model = detection_model
        self.cam_id = cam_id
        self.global_evaluator = global_evaluator
        self.id_to_name = {}   # mapping API id -> name

    def process_frame(self, frame, timestamp=None):
        """
        Xử lý 1 frame: detect người, random id, gửi API, update laps.
        """
        # ----- Detection YOLO -----
        detection_results = self.detection_model(frame, conf=0.5, iou=0.5, verbose=False)[0]

        ids, xyxy_boxes = [], []
        for box in detection_results.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls == 0:  # person
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                xyxy_boxes.append([x1, y1, x2, y2])
                ids.append(random.randint(1, 100))  # random id tạm

        if ids:
            try:
                # ----- Gửi API -----
                response = send_tracking_to_api(ids, xyxy_boxes, frame)
                if response and response.status_code == 200:
                    detections = []
                    api_data = response.json().get("data", [])
                    for entry in api_data:
                        uid = entry.get("id")            
                        infor = entry.get("infor", {})
                        metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                        name = metadata.get("name", "Unknown")
                        user_id = metadata.get("id", "Unknown")
                        self.id_to_name[user_id] = name
                        detections.append(user_id)

                    # ---- update qua GlobalEvaluator ----
                    self.global_evaluator.process_from_tracker(detections, self.cam_id, timestamp)

                else:
                    logger.error(f"API trả lỗi: {response.status_code if response else 'No response'}")
            except Exception as e:
                logger.error(f"Lỗi khi gửi API: {e}")

    def get_user_status(self, user_id):
        """Lấy số vòng & trạng thái camera của 1 user từ evaluator chung"""
        return self.global_evaluator.get_status(user_id)
