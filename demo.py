import gradio as gr
import cv2
import numpy as np
from ultralytics import YOLO
from src.tracking.detect import SimpleTracker
from src.engine.score import GlobalEvaluator

# --- setup ---
evaluator = GlobalEvaluator(id_run_process=[1, 2, 3, 4], test_mode=True)
trackers = {
    cam_id: SimpleTracker(
        detection_model=YOLO("/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt"),
        cam_id=cam_id,
        global_evaluator=evaluator
    )
    for cam_id in [1, 2, 3, 4]
}
result_store = {}

# --- generator function cho Gradio ---
def stream_videos(v1, v2, v3, v4):
    caps = {
        1: cv2.VideoCapture(v1),
        2: cv2.VideoCapture(v2),
        3: cv2.VideoCapture(v3),
        4: cv2.VideoCapture(v4),
    }

    while True:
        rets, frames = {}, {}
        for cam_id, cap in caps.items():
            ret, frame = cap.read()
            if not ret:
                return  # hết video
            frames[cam_id] = trackers[cam_id].process_frame(frame)

            # update result_store
            result_store[cam_id] = {
                user_id: evaluator.get_status(user_id)
                for user_id in evaluator.evaluator.laps.keys()
            }

        # ghép 4 frame thành layout 2x2
        top = np.hstack([frames[1], frames[2]])
        bottom = np.hstack([frames[3], frames[4]])
        merged = np.vstack([top, bottom])

        # convert BGR -> RGB để hiển thị
        merged_rgb = cv2.cvtColor(merged, cv2.COLOR_BGR2RGB)

        logs = str(result_store)
        yield merged_rgb, logs  # stream ra Gradio UI

# --- UI ---
with gr.Blocks() as demo:
    gr.Markdown("## 🎥 Fitness Tracking Stream Demo")

    with gr.Row():
        with gr.Column():
            v1 = gr.File(label="Video Cam 1", file_types=[".mp4"])
            v2 = gr.File(label="Video Cam 2", file_types=[".mp4"])
            v3 = gr.File(label="Video Cam 3", file_types=[".mp4"])
            v4 = gr.File(label="Video Cam 4", file_types=[".mp4"])
            btn = gr.Button("Start Streaming")
        with gr.Column():
            image_out = gr.Image(label="Merged Live Result", type="numpy")
            log_out = gr.Textbox(label="Log vòng chạy", lines=20)

    # stream generator -> Gradio
    btn.click(fn=stream_videos, 
              inputs=[v1, v2, v3, v4], 
              outputs=[image_out, log_out])

demo.launch()
