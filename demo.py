import threading
import queue
import time
import cv2
import gradio as gr
from ultralytics import YOLO
from src.tracking.detect import SimpleTracker
from src.engine.score import GlobalEvaluator

# ========= 1. Setup model & tracker =========
MODEL_PATH = "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt"

# Danh sách cam id
CAM_IDS = [1, 2, 3, 4]

evaluator = GlobalEvaluator(id_run_process=CAM_IDS, test_mode=True)
trackers = {
    cid: SimpleTracker(detection_model=YOLO(MODEL_PATH), cam_id=cid, global_evaluator=evaluator)
    for cid in CAM_IDS
}

# ========= 2. Queue để truyền frame =========
frame_queues: dict[int, queue.Queue] = {}


def worker(cid: int, path: str):
    """Đọc video và gửi frame vào queue."""
    cap = cv2.VideoCapture(path)
    if cid not in frame_queues:
        frame_queues[cid] = queue.Queue(maxsize=1)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        out_frame = trackers[cid].process_frame(frame)
        out_rgb = cv2.cvtColor(out_frame, cv2.COLOR_BGR2RGB)
        out_rgb = cv2.resize(out_rgb, (640, 360))

        q = frame_queues[cid]
        if q.full():
            try:
                q.get_nowait()
            except queue.Empty:
                pass
        q.put(out_rgb)

        time.sleep(0.01)

    cap.release()


# ========= 3. Stream cho Gradio =========
def stream_ui(path1, path2, path3, path4):
    sources = {1: path1, 2: path2, 3: path3, 4: path4}

    # khởi động worker cho các video được upload
    for cid, src in sources.items():
        if not src:  # nếu None hoặc rỗng thì bỏ qua
            continue
        if not any(t.name == f"worker-{cid}" for t in threading.enumerate()):
            t = threading.Thread(target=worker, args=(cid, src), daemon=True, name=f"worker-{cid}")
            t.start()

    # vòng lặp stream
    while True:
        frames = []
        for cid in CAM_IDS:
            if cid in frame_queues:
                try:
                    frm = frame_queues[cid].get(timeout=0.1)
                except queue.Empty:
                    frm = None
            else:
                frm = None
            frames.append(frm)

        try:
            with open(evaluator.evaluator.server_file, "r", encoding="utf-8") as f:
                server_json = f.read()
        except FileNotFoundError:
            server_json = "{}"

        yield (*frames, server_json)
        time.sleep(0.05)


# ========= 4. UI =========
with gr.Blocks() as demo:
    gr.Markdown("## 🎥 Fitness Tracking Stream Demo")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Row():
                v1_out = gr.Image(label="Cam 1", type="numpy")
                v2_out = gr.Image(label="Cam 2", type="numpy")
            with gr.Row():
                v3_out = gr.Image(label="Cam 3", type="numpy")
                v4_out = gr.Image(label="Cam 4", type="numpy")
        with gr.Column(scale=1):
            server_out = gr.Textbox(label="📂 Server JSON", lines=20)

    with gr.Row():
        file1 = gr.File(label="Video Cam 1", file_types=[".mp4", ".mov"])
        file2 = gr.File(label="Video Cam 2", file_types=[".mp4", ".mov"])
        file3 = gr.File(label="Video Cam 3", file_types=[".mp4", ".mov"])
        file4 = gr.File(label="Video Cam 4", file_types=[".mp4", ".mov"])
        btn = gr.Button("Start Streaming")

    btn.click(
        fn=stream_ui,
        inputs=[file1, file2, file3, file4],
        outputs=[v1_out, v2_out, v3_out, v4_out, server_out],
    )

demo.launch()
