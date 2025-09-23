import threading
import queue
import time
import cv2
import gradio as gr
import numpy as np
from loguru import logger
from confluent_kafka import Consumer
from ultralytics import YOLO
from src.tracking.detect import SimpleTracker
from src.engine.score import GlobalEvaluator
from src.depend.depend import mongo_db
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.kafka.kafka_process import video_worker, create_topic
from collections import OrderedDict
import pandas as pd

# ========= 1. Config =========
MODEL_PATH = "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]
TOPIC_TEMPLATE = "camera-{cid}"
NUM_PARTITIONS = 3

# Buffer frame cho Gradio: mỗi cam có queue giữ frame mới nhất
frame_buffers = {cid: queue.Queue(maxsize=1) for cid in CAM_IDS}

# Global evaluator & tracker
evaluator = GlobalEvaluator(id_run_process=CAM_IDS)
trackers = {
    cid: SimpleTracker(detection_model=YOLO(MODEL_PATH), cam_id=cid, global_evaluator=evaluator)
    for cid in CAM_IDS
}

# ========= 2. Kafka Producer =========
producer_conf = {
    'bootstrap.servers': '10.100.200.119:9098',
    'compression.type': 'lz4',
    'linger.ms': 10,
    'batch.num.messages': 10000,
    'message.max.bytes': 10000000,
}
producer = KafkaFrameProducer(producer_conf, topic_template="camera-{camera_id}", jpeg_quality=70, drop_on_full=True)

# ========= 3. Tạo topic =========
topics = [TOPIC_TEMPLATE.format(cid=cid) for cid in CAM_IDS]
create_topic(topics, number_of_partitions=NUM_PARTITIONS, host_servers='10.100.200.119:9098')

# ========= 4. Kafka Consumer worker =========
consumer_conf = {"bootstrap.servers": "10.100.200.119:9098", "group.id": "gradio-demo"}

def kafka_consumer_worker(cid):
    topic = TOPIC_TEMPLATE.format(cid=cid)
    consumer = KafkaFrameConsumer(consumer_conf, topic, group_id=f"group-{topic}")

    frame_dict = OrderedDict()  # tự động theo thứ tự insert

    def handle_frame(msg):
        headers = dict(msg.headers() or [])
        frame_index = int(headers.get(b'frame_index', b'0'))

        nparr = np.frombuffer(msg.value(), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        out_frame = trackers[cid].process_frame(frame)
        rgb_frame = cv2.cvtColor(out_frame, cv2.COLOR_BGR2RGB)
        rgb_frame = cv2.resize(rgb_frame, (640, 360))

        frame_dict[frame_index] = rgb_frame

        # Giữ tối đa 10 frame trong buffer
        if len(frame_dict) > 10:
            for i in sorted(frame_dict.keys())[:len(frame_dict)-10]:
                frame_dict.pop(i)

        # Luôn lấy **frame index liên tiếp tiếp theo** để hiển thị
        # Giả sử last_index là frame cuối cùng đã hiển thị
        if not hasattr(handle_frame, "last_index"):
            handle_frame.last_index = -1

        next_index = handle_frame.last_index + 1
        if next_index in frame_dict:
            if frame_buffers[cid].full():
                try:
                    frame_buffers[cid].get_nowait()
                except queue.Empty:
                    pass
            frame_buffers[cid].put(frame_dict[next_index])
            frame_dict.pop(next_index)
            handle_frame.last_index = next_index

    consumer.start(handle_frame)

def json_to_dataframe(data):
    """
    Chuyển list dict MongoDB thành pandas DataFrame 2 cột: 'Tên', 'Vòng'
    """
    if not data:
        return pd.DataFrame(columns=["Tên", "Vòng"])
    
    rows = []
    for item in data:
        rows.append({
            "Tên": item.get("name", ""),
            "Vòng": item.get("laps", "")
        })
    return pd.DataFrame(rows)

# ========= 5. Gradio stream =========
def stream_ui(path1, path2, path3, path4):
    sources = {1: path1, 2: path2, 3: path3, 4: path4}

    # start producer threads (dùng video_worker sẵn có)
    for cid, src in sources.items():
        if not src:
            continue
        if not any(t.name == f"producer-{cid}" for t in threading.enumerate()):
            t = threading.Thread(
                target=video_worker,
                args=(src, cid, producer),
                daemon=True,
                name=f"producer-{cid}"
            )
            t.start()

    # start consumer threads
    for cid in CAM_IDS:
        if not any(t.name == f"consumer-{cid}" for t in threading.enumerate()):
            t = threading.Thread(
                target=kafka_consumer_worker,
                args=(cid,),
                daemon=True,
                name=f"consumer-{cid}"
            )
            t.start()

    while True:
        frames = []
        for cid in CAM_IDS:
            try:
                frame = frame_buffers[cid].get(timeout=0.1)
            except queue.Empty:
                frame = None
            frames.append(frame)

        try:
            server_json = mongo_db.find_all("laps_db") or {}
        except Exception as e:
            logger.error(f"MongoDB error: {e}")
            server_json = {}

        server_df = json_to_dataframe(server_json)
        yield (*frames, server_df)
        time.sleep(0.03)  # ~30 FPS UI

# ========= 6. Gradio UI =========

with gr.Blocks() as demo:
    gr.Markdown("## 🎥 Fitness Tracking Stream Demo")
    with gr.Row():
        with gr.Column(scale=1):
            v1_out = gr.Image(label="Cam 1", type="numpy")
            v2_out = gr.Image(label="Cam 2", type="numpy")
            v3_out = gr.Image(label="Cam 3", type="numpy")
            v4_out = gr.Image(label="Cam 4", type="numpy")
        with gr.Column(scale=1):
            server_out = gr.Dataframe(
                label="📊 Server Table",
                headers=["Tên", "Vòng"],
                datatype=["str", "number"],
                interactive=False
            )
    with gr.Row():
        file_inputs = [gr.File(label=f"Video Cam {i}", file_types=[".mp4", ".mov"]) for i in CAM_IDS]
        btn = gr.Button("Start Streaming")
    btn.click(fn=stream_ui, inputs=file_inputs, outputs=[v1_out, v2_out, v3_out, v4_out, server_out])

demo.launch()
