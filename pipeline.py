import cv2
import json
import requests
from src.tracking.tracking import tracking_in_frame
from src.search.curl_api_search import curl_post
from ultralytics import YOLO
from src.config.config import CAMERA_INDEX, VIDEO_PATH
from src.camera.setting_camera import CameraSettings, CameraViewer
import time
from src.tracking.tracking import frame_tracking_callback


if __name__ == "__main__":
    camera = CameraViewer(
        camera_id=0,
        source=0,
        settings=CameraSettings(camera_id=0, width=640, height=480, fps=30),
        on_frame_callback=frame_tracking_callback
    )

    try:
        camera.start()
        while not camera.stop_flag:
            time.sleep(0.1)

    except KeyboardInterrupt:
        camera.stop()