from src.tracking.detect import SimpleTracker
from src.camera.setting_camera import CameraSettings, CameraViewer
from src.engine.score import GlobalEvaluator
# from tracking.utils import send_tracking_to_api, draw_target
from ultralytics import YOLO
import cv2
import time
from loguru import logger


# setup model YOLO
yolo_model = YOLO('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt')   # load model detect person

evaluator = GlobalEvaluator(id_run_process=[1, 2, 3, 4])
# setup tracker (ví dụ cam_id=1, chu trình 1→2→3)
trackers = {
    cam_id: SimpleTracker(detection_model=yolo_model, cam_id=cam_id, global_evaluator=evaluator)
    for cam_id in [1, 2, 3, 4]
}

result_store = {}
# callback cho CameraViewer
def make_callback(cam_id):
    def on_frame(frame, frame_idx):
        # process_frame đã gọi update qua GlobalEvaluator
        trackers[cam_id].process_frame(frame, timestamp=frame_idx)

        # lưu lại trạng thái hiện tại của tất cả user
        result_store[cam_id] = {
            user_id: evaluator.get_status(user_id) 
            for user_id in evaluator.evaluator.laps.keys()
        }

        return result_store[cam_id]
    return on_frame


viewers = [
    CameraViewer(camera_id=cam_id, source=r'/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/0.avi',
                 on_frame_callback=make_callback(cam_id),
                 save_results=True)
    for cam_id in [1, 2, 3, 4]
]

# start camera
# start tất cả camera
for v in viewers:
    v.start()

# giữ chương trình chạy cho đến khi tất cả stop
try:
    while any(not v.stop_flag for v in viewers):
        time.sleep(0.1)
except KeyboardInterrupt:
    for v in viewers:
        v.stop()


