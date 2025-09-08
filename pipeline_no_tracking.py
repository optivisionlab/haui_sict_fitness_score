from src.tracking.detect import SimpleTracker
from src.camera.setting_camera import CameraSettings, CameraViewer
from src.engine.score import GlobalEvaluator
# from tracking.utils import send_tracking_to_api, draw_target
from ultralytics import YOLO
import cv2
import time
from loguru import logger


# setup model YOLO
# yolo_model = YOLO('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt')   # load model detect person

evaluator = GlobalEvaluator(id_run_process=[1, 2, 3, 4], test_mode=True)  # chu trình 1→2→3-4
# setup tracker (ví dụ cam_id=1, chu trình 1→2→3)
trackers = {
    cam_id: SimpleTracker(detection_model=YOLO('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt'), cam_id=cam_id, global_evaluator=evaluator)
    for cam_id in [1, 2, 3, 4]
}

result_store = {}
# callback cho CameraViewer
def make_callback(cam_id):
    def on_frame(frame, frame_idx):
        # process_frame đã gọi update qua GlobalEvaluator
        frame_with_boxes = trackers[cam_id].process_frame(frame)

        # lưu lại trạng thái hiện tại của tất cả user
        result_store[cam_id] = {
            user_id: evaluator.get_status(user_id) 
            for user_id in evaluator.evaluator.laps.keys()
        }
        logger.info(f"[Cam {cam_id}] Frame {frame_idx} - Result: {result_store[cam_id]}")
        return frame_with_boxes
    return on_frame

video_sources = {
    1: r"D:\NCKH_Cham_diem_the_duc\assets\test\lan1\chaylan1.mp4",
    2: r"D:\NCKH_Cham_diem_the_duc\assets\test\lan1\chaylan1.2.mp4",
    3: r"D:\NCKH_Cham_diem_the_duc\assets\test\lan1\chaylan1.3.mp4",
    4: r"D:\NCKH_Cham_diem_the_duc\assets\test\lan1\chaylan1.4.mp4",
}

for cam_id in [1, 2, 3, 4]:
    viewer = CameraViewer(
        camera_id=cam_id,
        source=video_sources[cam_id],
        on_frame_callback=make_callback(cam_id),
        save_results=True,
    )
    viewer.start()
    viewer.thread.join()  # đợi chạy xong video



