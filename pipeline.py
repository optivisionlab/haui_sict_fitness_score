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
from src.tracking.deep_sort.tools import generate_detections as encoder
from src.tracking.deep_sort.deep_sort.nn_matching import NearestNeighborDistanceMetric
from src.tracking.deep_sort.deep_sort.tracker import Tracker
from src.tracking.deep_sort.deep_sort.detection import Detection
from src.search.curl_api_search import send_tracking_to_api


if __name__ == "__main__":
    model=YOLO('yolo11n.pt') # Chuyển model sang GPU nếu có
    encoding = encoder.create_box_encoder(
        "models/mars-small128.pb", batch_size=32
    )
    metric = NearestNeighborDistanceMetric("cosine", 0.5, None)
    tracker = Tracker(metric, max_age=90, n_init=10, max_iou_distance=0.5)

    camera = CameraViewer(
        camera_id=0,
        source=r'D:\NCKH_Cham_diem_the_duc\assets\2871418117583217428.mp4',
        settings=CameraSettings(camera_id=0, width=640, height=480, fps=60),
        on_frame_callback=lambda frame, idx: frame_tracking_callback(frame, idx, tracking_object=tracker, detection_model=model, encode_model=encoding),
        save_results=True,
        save_path=r'D:\NCKH_Cham_diem_the_duc\assets\tracking_results.avi'
    )

    try:
        camera.start()
        while not camera.stop_flag:
            time.sleep(0.1)

    except KeyboardInterrupt:
        camera.stop()
    # tracking_in_frame(source=r'D:\NCKH_Cham_diem_the_duc\assets\169576879170534422.mp4', model=YOLO('yolo11n.pt'), target_class=0, api_call_interval=30)