import time
import random
from typing import Dict, List, Tuple
from loguru import logger

from src.engine.curl_api_search import send_tracking_to_api
from src.engine.engine import draw_target
from src.config.config import LINE_BEGIN_SEARCH, QDRANT_COLLECTION


class SimpleTracker:
    """
    No real tracking yet:
    - Detect only (YOLO.predict / YOLO()).
    - Generate TEMP random ids ONLY for mapping in face-search response.
    """

    def __init__(self, detection_model, cam_id):
        self.detection_model = detection_model
        self.cam_id = cam_id
        self._rng = random.SystemRandom()

    def _gen_unique_ids(self, n: int) -> List[int]:
        # random but guaranteed unique within one request
        s = set()
        while len(s) < n:
            s.add(self._rng.randint(1, 2_147_483_647))  # 31-bit int
        return list(s)

    def detect_frame(self, frame):
        # detect only (no track)
        result = self.detection_model(frame, conf=0.65, iou=0.8, verbose=False)[0]

        boxes: List[List[int]] = []
        if result is None or result.boxes is None:
            return [], [], frame

        for box in result.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls != 0:  # only person
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            boxes.append([x1, y1, x2, y2])

        ids = self._gen_unique_ids(len(boxes))
        return ids, boxes, frame


    def detect_batch(self, frames: List):
        results = self.detection_model(frames, conf=0.65, iou=0.8, verbose=False)

        outs = []
        for frame, res in zip(frames, results):
            boxes: List[List[int]] = []
            if res is not None and res.boxes is not None:
                for box in res.boxes:
                    cls = int(box.cls[0]) if box.cls is not None else -1
                    if cls != 0:
                        continue
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    boxes.append([x1, y1, x2, y2])

            ids = self._gen_unique_ids(len(boxes))
            outs.append((ids, boxes, frame))

        return outs
    
    
class APIHandler:
    def __init__(self, evaluator, collection_name=QDRANT_COLLECTION):
        self.evaluator = evaluator
        self.collection_name = collection_name

        # cooldown per user to prevent double count
        self._user_cooldown_until: Dict[str, float] = {}
        self.user_cooldown_seconds = 1.0

        # per-cam gate to reduce API spam
        self._cam_last_call_ts: Dict[str, float] = {}
        self.cam_call_min_interval = 0.03  # seconds

        # line band (hysteresis) around the line to approximate "crossing"
        self.band_ratio = 0.06  # 6% of image height

    def __draw_detections__(self, frame, detection):
        user_id, box = detection
        draw_target(frame, user_id, box, name="", color=(0, 255, 0), thickness=2)
        return frame

    def _center_y(self, box_xyxy: List[int]) -> float:
        return (box_xyxy[1] + box_xyxy[3]) / 2.0

    def _is_below_line(self, box, y_line: float, mode: str = "xyxy") -> bool:
        """
        Return True if bbox center is below the line (strictly below).
        mode:
        - "xyxy": box = [x1, y1, x2, y2]
        - "xywh": box = [x_center, y_center, w, h]
        """
        if mode == "xyxy":
            x1, y1, x2, y2 = box
            y_center = (y1 + y2) / 2.0
        else:
            _, y_center, _, _ = box
        return y_center > y_line

    async def process(self, cam_id, frame, xyxy_boxes, ids, timestamp=None):
        now = float(timestamp) if timestamp is not None else time.time()
        logger.debug("Processing detections for cam_id={}, frame_time={}".format(cam_id, timestamp))
        cam_id = str(cam_id)

        # per-cam rate limit: avoid calling search too frequently in high FPS
        last = self._cam_last_call_ts.get(cam_id, 0.0)
        if now - last < self.cam_call_min_interval:
            logger.debug(f"Skipping API call for cam {cam_id} due to rate limit ({now - last:.2f}s since last call)")
            return

        y_line = int(frame.shape[0] * LINE_BEGIN_SEARCH)

        # keep only boxes in scoring zone (below line)
        valid_ids: List[int] = []
        valid_boxes: List[List[int]] = []
        for rid, box in zip(ids, xyxy_boxes):
            if self._is_below_line(box, y_line, mode="xyxy"):
                valid_ids.append(rid)
                valid_boxes.append(box)

        if not valid_ids:
            return

        try:
            response = await send_tracking_to_api(
                valid_ids,
                valid_boxes,
                frame,
                collection_name=self.collection_name,
                crop_mode="none",
            )
            if not response or response.status_code != 200:
                return
            self._cam_last_call_ts[cam_id] = now

            api_data = response.json().get("data", [])
            map_local_to_user = {}
            for entry in api_data:
                sent_local_id = entry.get("id")
                infor = entry.get("infor", {}) or {}
                metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                user_id = metadata.get("id") or metadata.get("user_id") or metadata.get("uid")
                if sent_local_id is not None and user_id is not None:
                    map_local_to_user[int(sent_local_id)] = str(user_id)

            detections = []
            for local_id, box in zip(valid_ids, valid_boxes):
                uid = map_local_to_user.get(int(local_id))
                if uid:
                    detections.append([uid, box])

            for user_id, box in detections:
                until = self._user_cooldown_until.get(user_id, 0.0)
                if now < until:
                    continue

                draw_frame = None
                if self.evaluator.cfg.upload_each_checkin:
                    draw_frame = self.__draw_detections__(frame.copy(), [user_id, box])
                ok = self.evaluator.set_flag_redis(user_id, cam_id, draw_frame, timestamp=timestamp)
                if not ok:
                    continue

                lap_done = self.evaluator.check_lap_1_user(user_id)
                if lap_done:
                    # 1) log
                    logger.info("✅ user {} completed a lap (cam={})", user_id, cam_id)
                    # 2) set cooldown to prevent double count
                    self._user_cooldown_until[user_id] = now + self.user_cooldown_seconds

        except Exception as e:
            logger.exception(f"API search error: {e}")
