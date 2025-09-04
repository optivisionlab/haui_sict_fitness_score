from src.tracking.detect import SimpleTracker
from src.camera.setting_camera import CameraSettings, CameraViewer
from src.engine.score import GlobalEvaluator
# from tracking.utils import send_tracking_to_api, draw_target
from ultralytics import YOLO
import cv2
import time


# setup model YOLO
yolo_model = YOLO()   # load model detect person

evaluator = GlobalEvaluator(id_run_process=[1, 2, 3, 4])
# setup tracker (ví dụ cam_id=1, chu trình 1→2→3)
trackers = {
    cam_id: SimpleTracker(detection_model=yolo_model, id_run_process=[1,2,3,4], cam_id=cam_id)
    for cam_id in [1, 2, 3, 4]
}

result_store = {}
# callback cho CameraViewer
def make_callback(cam_id):
    def on_frame(frame, frame_idx):
        detections = trackers[cam_id].process_frame(frame)   # list user_id
        results = evaluator.process_detection(detections, cam_id, timestamp=frame_idx)
        result_store[cam_id] = results
        return results
    return on_frame

viewers = [
    CameraViewer(camera_id=cam_id, source=r'D:\NCKH_Cham_diem_the_duc\assets\2871418117583217428.mp4',
                 on_frame_callback=make_callback(cam_id),
                 save_results=True)
    for cam_id in [1]
]

# start camera
for v in viewers:
    v.start()
    while not v.stop_flag:
        time.sleep(0.1)

