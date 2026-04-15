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

# from src.config.config import SEARCH_API_URL
import httpx
import asyncio
from typing import Optional

from src.config.config import get_search_api_url


_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_async_client() -> httpx.AsyncClient:
    global _client
    if _client is not None:
        return _client

    async with _client_lock:
        if _client is None:
            timeout = httpx.Timeout(connect=2.0, read=8.0, write=8.0, pool=2.0)
            limits = httpx.Limits(
                max_connections=8,
                max_keepalive_connections=4,
                keepalive_expiry=30.0,
            )
            _client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                headers={"accept": "application/json"},
            )
        return _client


async def close_async_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def http_post_async(url, data=None, files=None):
    client = await get_async_client()
    try:
        response = await client.post(url, data=data, files=files)
        return response
    except httpx.HTTPError as e:
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


async def send_tracking_to_api(
    ids,
    xyxy_boxes,
    frame,
    collection_name="face",
    *,
    cam_id=None,
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
    logger.info("Prepared payload for search API: {}", payload)
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
    base_url = get_search_api_url(cam_id)
    request_url = f"{base_url}/faces/search"
    logger.info("Calling search API for cam_id={} -> {}", cam_id, request_url)
    return await http_post_async(
        url=request_url,
        data=payload,
        files=files,
    )