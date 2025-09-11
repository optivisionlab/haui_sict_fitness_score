import gradio as gr
import cv2
import json
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
        for cam_id, cap in caps.items():
            ret, frame = cap.read()
            if not ret:
                return  # hết video
            trackers[cam_id].process_frame(frame)

        # cập nhật log
        logs = {
            user_id: evaluator.get_status(user_id)
            for user_id in evaluator.evaluator.laps.keys()
        }

        # đọc file JSON server giả tưởng
        try:
            with open(evaluator.evaluator.server_file, "r", encoding="utf-8") as f:
                server_json = f.read()
        except FileNotFoundError:
            server_json = "{}"

        # stream ra Gradio UI
        yield server_json


# --- UI ---
with gr.Blocks() as demo:
    gr.Markdown("## 🎥 Fitness Tracking Stream Demo")

    with gr.Row():
        with gr.Column():
            v1 = gr.File(label="Video Cam 1", file_types=[".mp4", ".mov"])
            v2 = gr.File(label="Video Cam 2", file_types=[".mp4", ".mov"])
            v3 = gr.File(label="Video Cam 3", file_types=[".mp4", ".mov"])
            v4 = gr.File(label="Video Cam 4", file_types=[".mp4", ".mov"])
            btn = gr.Button("Start Streaming")
        with gr.Column():
            # log_out = gr.Textbox(label="Log vòng chạy", lines=10)
            server_out = gr.Textbox(label="📂 Server JSON", lines=20)

    btn.click(
        fn=stream_videos,
        inputs=[v1, v2, v3, v4],
        outputs=[server_out]
    )

demo.launch()

