"""HTTP client for face-search used in realtime pipeline.

Key goals:
- Fast + resilient (reuse Session + retries)
- Smaller payload (optional union-crop)
- Avoid fake-async (previous code declared async but used blocking requests)
"""

import json
from typing import List, Tuple

import cv2
import numpy as np
import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.config import SEARCH_API_URL


def _build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("POST", "PUT"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=64, pool_maxsize=64)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


session = _build_session()


def curl_post(url, payload=None, files=None, headers=None, method="POST"):
    if headers is None:
        headers = {"accept": "application/json"}

    try:
        response = session.request(
            method,
            url,
            headers=headers,
            data=payload,
            files=files,
            timeout=(2, 8),  # (connect, read)
        )
        return response
    except requests.RequestException as e:
        logger.error("HTTP error calling face-search: {}", e)
        return None


def _union_crop(frame: np.ndarray, boxes_xyxy: List[List[int]], pad_ratio: float = 0.25) -> Tuple[np.ndarray, List[List[int]]]:
    """Crop to union of boxes (with padding) to reduce upload size."""
    h, w = frame.shape[:2]
    xs1 = [b[0] for b in boxes_xyxy]
    ys1 = [b[1] for b in boxes_xyxy]
    xs2 = [b[2] for b in boxes_xyxy]
    ys2 = [b[3] for b in boxes_xyxy]
    x1, y1, x2, y2 = min(xs1), min(ys1), max(xs2), max(ys2)
    bw, bh = max(1, x2 - x1), max(1, y2 - y1)
    pad_x, pad_y = int(bw * pad_ratio), int(bh * pad_ratio)
    cx1, cy1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
    cx2, cy2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
    cropped = frame[cy1:cy2, cx1:cx2]
    adj = [[b[0] - cx1, b[1] - cy1, b[2] - cx1, b[3] - cy1] for b in boxes_xyxy]
    return cropped, adj


def send_tracking_to_api(
    ids,
    xyxy_boxes,
    frame,
    collection_name="face",
    *,
    similarity_threshold: float = 0.7,
    crop_mode: str = "union",  # "union" | "none"
):
    if not ids or frame is None:
        return None

    tracking_frame = json.dumps({"id": ids, "bbox": xyxy_boxes})
    payload = {
        "collection_name": collection_name,
        "tracking_frame": tracking_frame,
        "similarity_threshold": similarity_threshold,
    }

    upload_frame = frame
    if crop_mode == "union" and len(xyxy_boxes) > 0:
        try:
            upload_frame, adj_boxes = _union_crop(frame, xyxy_boxes)
            payload["tracking_frame"] = json.dumps({"id": ids, "bbox": adj_boxes})
        except Exception:
            upload_frame = frame

    success, encoded_image = cv2.imencode(".jpg", upload_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not success:
        return None

    if not isinstance(encoded_image, np.ndarray):
        encoded_image = np.array(encoded_image)

    files = [("images", ("frame.jpg", encoded_image.tobytes(), "image/jpeg"))]

    return curl_post(
        url=f"{SEARCH_API_URL}/faces/search",
        payload=payload,
        files=files,
        method="POST",
    )