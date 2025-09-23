import random
from collections import defaultdict

# Giả sử đã import sẵn
from src.search.curl_api_search import send_tracking_to_api
from ultralytics import YOLO
from loguru import logger
from src.engine.engine import draw_target, line_begin_curl_api_search
import cv2
from src.config.config import LINE_BEGIN_SEARCH, QDRANT_COLLECTION


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
        frame_with_boxes = frame.copy()
        logger.info('shape: {}', frame_with_boxes.shape)
        detection_results = self.detection_model(frame, conf=0.5, iou=0.5, verbose=False)[0]

        ids, xyxy_boxes = [], []
        for box in detection_results.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls == 0:  # person
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                xyxy_boxes.append([x1, y1, x2, y2])
                ids.append(random.randint(1, 100))  # random id tạm
        logger.info(f"Detected {len(ids)} persons in camera {self.cam_id}")

        cv2.line(frame_with_boxes, (0, int(frame.shape[0]*LINE_BEGIN_SEARCH)), (frame.shape[1], int(frame.shape[0]*LINE_BEGIN_SEARCH)), (0, 0, 255), 2)
        
        valid_ids, valid_boxes = [], []
        for uid, box in zip(ids, xyxy_boxes):
            if line_begin_curl_api_search((0, int(frame.shape[0]*LINE_BEGIN_SEARCH)), box, mode='xyxy'):
                valid_ids.append(uid)
                valid_boxes.append(box)

        logger.info('valid_ids, valid_boxes: {}, {}'.format(valid_ids, valid_boxes))
        if valid_ids:
            try:
                # Gửi API chỉ những người vượt line
                response = send_tracking_to_api(valid_ids, valid_boxes, frame, collection_name=QDRANT_COLLECTION)

                # map từ local_id (bạn gửi) -> (user_id, name) do API trả
                map_local_to_user = {}
                if response and response.status_code == 200:
                    api_data = response.json().get("data", [])
                    for entry in api_data:
                        sent_local_id = entry.get("id")
                        infor = entry.get("infor", {}) or {}
                        metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                        user_id = metadata.get("id") or metadata.get("user_id") or metadata.get("uid")
                        name = metadata.get("name", "Unknown")
                        if sent_local_id is not None:
                            try:
                                key = int(sent_local_id)
                            except Exception:
                                key = sent_local_id
                            map_local_to_user[key] = (str(user_id) if user_id is not None else None, name)
                            if user_id is not None:
                                # lưu tên theo user_id để dùng cho lần sau
                                self.id_to_name[str(user_id)] = name

                detections = []
                # Vẽ chỉ các valid boxes — dùng mapping để lấy user_id + name
                for local_id, box in zip(valid_ids, valid_boxes):
                    pair = map_local_to_user.get(local_id)
                    if pair and pair[0] is not None:
                        user_id, name = pair
                        draw_target(frame_with_boxes, user_id, box, name=name, color=(0, 255, 0), thickness=2)
                        detections.append(name)
                    else:
                        # nếu API không trả mapping cho local_id này, có thể vẽ "Unknown" hoặc bỏ vẽ
                        draw_target(frame_with_boxes, local_id, box, name='Unknown', color=(0, 255, 255), thickness=1)

                # update evaluator bằng danh sách user_id thực (nếu có)
                if detections:
                    self.global_evaluator.process_from_tracker(detections, self.cam_id)

            except Exception as e:
                logger.exception(f"Lỗi khi gửi API: {e}")

        return frame_with_boxes

