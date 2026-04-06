import time
import random
from typing import Dict, List, Tuple, Optional
from loguru import logger

from src.engine.curl_api_search import send_tracking_to_api
from src.engine.engine import draw_target
from src.config.config import LINE_BEGIN_SEARCH, QDRANT_COLLECTION
import cv2


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

    @staticmethod
    def _intersection_over_box(box_xyxy: List[int], zone_xyxy: List[int]) -> float:
        bx1, by1, bx2, by2 = box_xyxy
        zx1, zy1, zx2, zy2 = zone_xyxy

        ix1 = max(bx1, zx1)
        iy1 = max(by1, zy1)
        ix2 = min(bx2, zx2)
        iy2 = min(by2, zy2)

        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0

        inter = (ix2 - ix1) * (iy2 - iy1)
        box_area = max(1, (bx2 - bx1) * (by2 - by1))
        return inter / box_area

    def detect_frame(
        self,
        frame,
        call_zone_xyxy: Optional[List[int]] = None,
        min_overlap_ratio: float = 0.8,
    ):
        result = self.detection_model(frame, conf=0.65, iou=0.8, verbose=False, save=True)[0]

        boxes: List[List[int]] = []
        if result is None or result.boxes is None:
            return [], [], frame

        for box in result.boxes:
            cls = int(box.cls[0]) if box.cls is not None else -1
            if cls != 0:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            person_box = [x1, y1, x2, y2]

            if call_zone_xyxy is not None:
                ratio = self._intersection_over_box(person_box, call_zone_xyxy)
                if ratio < min_overlap_ratio:
                    continue

            boxes.append(person_box)
            logger.info(f"Detected person box: {person_box} with confidence {box.conf[0].item():.2f}")
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

        # cooldown per user to prevent double count (stored in milliseconds)
        self._user_cooldown_until_ms: Dict[str, int] = {}
        self.user_cooldown_ms = 10  # 1s in milliseconds

        # per-cam gate to reduce API spam (timestamps stored in milliseconds)
        self._cam_last_call_ts_ms: Dict[str, int] = {}
        self.cam_call_min_interval_ms = 3  # milliseconds

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
        cam_id = str(cam_id)

        # monotonic clock in milliseconds for rate limiting / cooldowns
        now_mono_ms = time.perf_counter_ns() // 1_000_000
        # event timestamp in milliseconds since epoch (from headers) or current time
        event_ts_ms = int(timestamp) if timestamp is not None else time.time_ns() // 1_000_000

        # per-camera rate limit
        last_call_ms = self._cam_last_call_ts_ms.get(cam_id, 0)
        if now_mono_ms - last_call_ms < self.cam_call_min_interval_ms:
            logger.warning(
                f"Skipping API call for cam {cam_id} due to rate limit "
                f"({now_mono_ms - last_call_ms}ms since last call)"
            )
            return

        try:
            response = await send_tracking_to_api(
                ids,
                xyxy_boxes,
                frame,
                collection_name=self.collection_name,
                cam_id=cam_id,
                crop_mode="none",
            )
            if not response or response.status_code != 200:
                logger.warning("Search API returned no response")
                return

            logger.info("Search API status={} cam_id={}", response.status_code, cam_id)
            logger.info("Search API raw body: {}", response.text)

            if response.status_code != 200:
                return
            # update last-call timestamp for this camera (monotonic, in ms)
            self._cam_last_call_ts_ms[cam_id] = now_mono_ms

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
            for local_id, box in zip(ids, xyxy_boxes):
                uid = map_local_to_user.get(int(local_id))
                if uid:
                    detections.append([uid, box])

            for user_id, box in detections:
                # per-user cooldown based on monotonic milliseconds
                until_ms = self._user_cooldown_until_ms.get(user_id, 0)
                if now_mono_ms < until_ms:
                    continue

                draw_frame = None
                if self.evaluator.cfg.upload_each_checkin:
                    draw_frame = cv2.cvtColor(self.__draw_detections__(frame.copy(), [user_id, box]), cv2.COLOR_BGR2RGB)

                ok = self.evaluator.set_flag_redis(
                    user_id,
                    cam_id,
                    copy_frame=draw_frame,
                    timestamp=event_ts_ms,
                )
                if not ok:
                    logger.exception(f"User {user_id} is already in cooldown for cam {cam_id}")
                    

                lap_done = self.evaluator.check_lap_1_user(user_id)
                if lap_done:
                    # 1) log
                    logger.info("✅ user {} completed a lap (cam={})", user_id, cam_id)
                    # 2) set cooldown to prevent double count (store in ms)
                    self._user_cooldown_until_ms[user_id] = now_mono_ms + self.user_cooldown_ms

        except Exception as e:
            logger.exception(f"API search error: {e}")
