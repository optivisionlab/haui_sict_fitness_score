import time
import random
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set
from loguru import logger

from src.engine.curl_api_search import send_tracking_to_api
from src.engine.engine import draw_target
from src.config.config import (
    LINE_BEGIN_SEARCH,
    QDRANT_COLLECTION,
    TRACKING_CONF,
    TRACKING_IOU,
    SAVE_TRACKING,
    API_HANDLER_USER_COOLDOWN_MS,
    API_HANDLER_CAM_CALL_MIN_INTERVAL_MS,
    API_HANDLER_BAND_RATIO,
    SEARCH_API_CROP_MODE,
)
import cv2


class SimpleTracker:
    """
    No real tracking yet:
    - Detect only (YOLO.predict / YOLO()).
    - Generate TEMP random ids ONLY for mapping in face-search response.
    """

    def __init__(self, detection_model, cam_id, tracker_config: Optional[str] = None):
        self.detection_model = detection_model
        self.cam_id = cam_id
        self._rng = random.SystemRandom()
        self.tracker_config = tracker_config

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
        result = self.detection_model.track(
            frame,
            conf=TRACKING_CONF,
            iou=TRACKING_IOU,
            verbose=False,
            save=SAVE_TRACKING,
            persist=True,
            tracker=self.tracker_config,
            classes=[0],
        )[0]

        track_ids: List[int] = []
        boxes: List[List[int]] = []

        if result is None or result.boxes is None:
            return [], [], frame

        boxes_obj = result.boxes
        if boxes_obj.id is None:
            return [], [], frame

        id_list = boxes_obj.id.int().cpu().tolist()
        xyxy_list = boxes_obj.xyxy.int().cpu().tolist()
        cls_list = boxes_obj.cls.int().cpu().tolist() if boxes_obj.cls is not None else [0] * len(id_list)
        conf_list = boxes_obj.conf.cpu().tolist() if boxes_obj.conf is not None else [0.0] * len(id_list)

        for track_id, xyxy, cls_id, conf in zip(id_list, xyxy_list, cls_list, conf_list):
            if cls_id != 0:
                continue

            person_box = [int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])]

            if call_zone_xyxy is not None:
                ratio = self._intersection_over_box(person_box, call_zone_xyxy)
                if ratio < min_overlap_ratio:
                    continue

            track_ids.append(int(track_id))
            boxes.append(person_box)
            logger.info(
                f"Tracked person box: {person_box} with confidence {conf:.2f}, track_id={track_id}"
            )

        return track_ids, boxes, frame


    def detect_batch(self, frames: List):
        results = self.detection_model(
            frames,
            conf=TRACKING_CONF,
            iou=TRACKING_IOU,
            verbose=False,
        )

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
        self.user_cooldown_ms = API_HANDLER_USER_COOLDOWN_MS  # 1s in milliseconds

        # per-cam gate to reduce API spam (timestamps stored in milliseconds)
        self._cam_last_call_ts_ms: Dict[str, int] = {}
        self.cam_call_min_interval_ms = API_HANDLER_CAM_CALL_MIN_INTERVAL_MS  # milliseconds

        self._successful_tracks: Dict[str, Set[int]] = defaultdict(set)
        # line band (hysteresis) around the line to approximate "crossing"
        self.band_ratio = API_HANDLER_BAND_RATIO  # 6% of image height

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

        if not ids or not xyxy_boxes:
            return

        # ids ở đây chính là track_ids từ producer
        incoming_pairs = [
            (int(track_id), box)
            for track_id, box in zip(ids, xyxy_boxes)
        ]

        # bỏ các track đã match thành công trước đó
        pending_pairs = [
            (track_id, box)
            for track_id, box in incoming_pairs
            if track_id not in self._successful_tracks[cam_id]
        ]

        if not pending_pairs:
            logger.info(f"Skip search API for cam {cam_id}: all tracks already successful")
            return

        pending_track_ids = [track_id for track_id, _ in pending_pairs]
        pending_boxes = [box for _, box in pending_pairs]

        now_mono_ms = time.perf_counter_ns() // 1_000_000
        last_call_ms = self._cam_last_call_ts_ms.get(cam_id, 0)
        if now_mono_ms - last_call_ms < self.cam_call_min_interval_ms:
            logger.warning(
                f"Skipping API call for cam {cam_id} due to rate limit "
                f"({now_mono_ms - last_call_ms}ms since last call)"
            )
            return
        logger.warning(
            f"API call check passed for cam {cam_id} "
        )

        try:
            logger.error(
                f"Calling search API for cam {cam_id} with {len(pending_track_ids)} pending tracks"
            )
            start_time = time.time()
            response = await send_tracking_to_api(
                pending_track_ids,
                pending_boxes,
                frame,
                collection_name=self.collection_name,
                cam_id=cam_id,
                crop_mode=SEARCH_API_CROP_MODE,
            )
            logger.info(f"API call latency: {(time.time() - start_time):.2f}s")

            if not response or response.status_code != 200:
                logger.warning("Search API returned no response")
                return

            logger.info("Search API status={} cam_id={}", response.status_code, cam_id)
            logger.debug("Search API response: {}", response.text)
            self._cam_last_call_ts_ms[cam_id] = now_mono_ms

            api_data = response.json().get("data", [])
            map_track_to_user = {}

            for entry in api_data:
                sent_track_id = entry.get("id")
                infor = entry.get("infor", {}) or {}
                metadata = infor.get("metadata", {}) if isinstance(infor, dict) else {}
                user_id = metadata.get("id") or metadata.get("user_id") or metadata.get("uid")

                if sent_track_id is not None and user_id is not None:
                    map_track_to_user[int(sent_track_id)] = str(user_id)

            detections = []
            for track_id, box in pending_pairs:
                uid = map_track_to_user.get(int(track_id))
                if uid:
                    detections.append((track_id, uid, box))

            if not detections:
                logger.info(f"No matched user returned from search API for cam {cam_id}")
                return

            for track_id, user_id, box in detections:
                until_ms = self._user_cooldown_until_ms.get(user_id, 0)
                if now_mono_ms < until_ms:
                    continue

                draw_frame = None
                if self.evaluator.cfg.upload_each_checkin:
                    draw_frame = cv2.cvtColor(
                        self.__draw_detections__(frame.copy(), [user_id, box]),
                        cv2.COLOR_BGR2RGB,
                    )

                ok = self.evaluator.set_flag_redis(
                    user_id,
                    cam_id,
                    copy_frame=draw_frame,
                )
                if not ok:
                    logger.exception(f"User {user_id} is already in cooldown for cam {cam_id}")

                # chỉ khi có match user thì mới coi track này là thành công
                self._successful_tracks[cam_id].add(int(track_id))
                logger.info(
                    "Marked successful track cam_id={} track_id={} -> user_id={}",
                    cam_id,
                    track_id,
                    user_id,
                )

                lap_done = self.evaluator.check_lap_1_user(user_id)
                if lap_done:
                    logger.info("✅ user {} completed a lap (cam={})", user_id, cam_id)
                    self._user_cooldown_until_ms[user_id] = now_mono_ms + self.user_cooldown_ms

        except Exception as e:
            logger.exception(f"API search error: {e}")
