import random
from collections import defaultdict

# Giả sử đã import sẵn
from src.search.curl_api_search import send_tracking_to_api
from ultralytics import YOLO
from loguru import logger
from src.engine.engine import draw_target, line_begin_curl_api_search
import cv2
from src.config.config import LINE_BEGIN_SEARCH, QDRANT_COLLECTION
import torch
import asyncio


class SimpleTracker:
    def __init__(self, detection_model, cam_id):
        """
        detection_model: YOLO model để detect người
        cam_id: camera hiện tại
        global_evaluator: đối tượng GlobalEvaluator (chung cho mọi tracker)
        """
        # ở đây KHÔNG load YOLO lại nữa, chỉ dùng model truyền vào
        self.detection_model = detection_model
        self.cam_id = cam_id
        self.id_to_name = {}   # mapping API id -> name


    def _parse_result(self, frame, detection_result):
        ids, xyxy_boxes = [], []
        for box in detection_result.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls == 0:  # person
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                xyxy_boxes.append([x1, y1, x2, y2])
                ids.append(random.randint(1, 100))
        logger.info(f"Detected {len(ids)} persons in camera {self.cam_id}")
        return ids, xyxy_boxes, frame


    def detect_frame(self, frame):
        try:
            result = self.detection_model(frame, conf=0.5, iou=0.5, verbose=False)[0]
            return self._parse_result(frame, result)
        finally:
            torch.cuda.empty_cache()

    def detect_batch(self, frames):
        with torch.inference_mode():
            results = self.detection_model(frames, conf=0.6, iou=0.7, verbose=False, device=0)
            return [self._parse_result(frame, res) for frame, res in zip(frames, results)]
    

class APIHandler:
    def __init__(self, evaluator, lap_update, collection_name=QDRANT_COLLECTION):
        self.evaluator = evaluator
        self.lap_update = lap_update
        self.collection_name = collection_name
        self.id_to_name = {}

    def __draw_detections__(self, frame, detections):
        for detection in detections:
            user_id, box = detection
            draw_target(frame, user_id, box, name="", color=(0, 255, 0), thickness=2)
        return frame

    def process(self, cam_id, frame, xyxy_boxes, ids, timestamp=None):
        copy_frame = frame.copy()

        valid_ids, valid_boxes = [], []
        for uid, box in zip(ids, xyxy_boxes):
            if line_begin_curl_api_search((0, int(copy_frame.shape[0]*LINE_BEGIN_SEARCH)), box, mode='xyxy'):
                valid_ids.append(uid)
                valid_boxes.append(box)

        logger.info('valid_ids, valid_boxes: {}, {}'.format(valid_ids, valid_boxes))
        if not valid_ids:
            return

        try:
            response = asyncio.run(send_tracking_to_api(valid_ids, valid_boxes, copy_frame, collection_name=self.collection_name))

            map_local_to_user = {}
            if response and response.status_code == 200:
                api_data = response.json().get("data", [])
                for entry in api_data:
                    sent_local_id = entry.get("id")
                    infor = entry.get("infor", {}) or {}
                    metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                    user_id = metadata.get("id") or metadata.get("user_id") or metadata.get("uid")
                    name = metadata.get("name", "Person")
                    if sent_local_id is not None:
                        try:
                            key = int(sent_local_id)
                        except Exception:
                            key = sent_local_id
                        map_local_to_user[key] = (str(user_id) if user_id is not None else None, name)
                        if user_id is not None:
                            self.id_to_name[str(user_id)] = name

            detections = []
            for local_id, box in zip(valid_ids, valid_boxes):
                pair = map_local_to_user.get(local_id)
                if pair and pair[0] is not None:
                    user_id, name = pair
                    # draw_target(copy_frame, user_id, box, name=name, color=(0, 255, 0), thickness=2)
                    detections.append([user_id, box])

            if detections:
                for detection in detections:
                    user_id, box = detection
                    logger.debug(f'user_id: {user_id}, cam_id: {cam_id}')
                    draw_frame = self.__draw_detections__(copy_frame, detections)
                    self.evaluator.set_flag_redis(user_id, cam_id, draw_frame, timestamp=timestamp)
                    self.evaluator.check_lap_1_user(user_id)

        except Exception as e:
            logger.exception(f"Lỗi khi gửi API: {e}")

