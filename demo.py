import threading
import queue
import time
import cv2
import gradio as gr
import numpy as np
from loguru import logger
from ultralytics import YOLO
from collections import OrderedDict
import pandas as pd

from src.tracking.detect import SimpleTracker
from src.engine.score import GlobalEvaluator
from src.depend.depend import mongo_db
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.kafka.kafka_process import video_worker, create_topic

# ========= 1. Config =========
MODEL_PATH = "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]
TOPIC_TEMPLATE = "camera-{cid}"
NUM_PARTITIONS = 1
FPS_TARGET = 20
FRAME_INTERVAL = 1.0 / FPS_TARGET

# Buffer frame cho Gradio: mỗi cam có queue giữ frame mới nhất
frame_buffers = {cid: queue.Queue(maxsize=1) for cid in CAM_IDS}

# Global evaluator & tracker
evaluator = GlobalEvaluator(id_run_process=CAM_IDS)
trackers = {
    cid: SimpleTracker(detection_model=YOLO(MODEL_PATH), cam_id=cid, global_evaluator=evaluator)
    for cid in CAM_IDS
}

# ========= 2. Kafka Producer per camera =========
producer_conf = {
    'bootstrap.servers': '10.100.200.119:9098',
    'compression.type': 'lz4',
    'linger.ms': 1,
    'batch.num.messages': 500,
    'message.max.bytes': 10000000,
}

producers = {
    cid: KafkaFrameProducer(
        producer_conf,
        topic_template=f"camera-{cid}",
        jpeg_quality=70,
        drop_on_full=True,
    )
    for cid in CAM_IDS
}

# ========= 3. Tạo topic =========
topics = [TOPIC_TEMPLATE.format(cid=cid) for cid in CAM_IDS]
create_topic(topics, number_of_partitions=NUM_PARTITIONS, host_servers='10.100.200.119:9098')

# ========= 4. Kafka Consumer worker =========
consumer_conf = {"bootstrap.servers": "10.100.200.119:9098", "group.id": "gradio-demo"}

def kafka_consumer_worker(cid):
    topic = TOPIC_TEMPLATE.format(cid=cid)
    consumer = KafkaFrameConsumer(consumer_conf, topic, group_id=f"group-{topic}")
    frame_dict = OrderedDict()

    def handle_frame(msg):
        headers = dict(msg.headers() or [])
        frame_index = int(headers.get(b'frame_index', b'0'))

        nparr = np.frombuffer(msg.value(), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        ids, boxes = trackers[cid].detect_frame(frame)
        # out_frame = trackers[cid].handle_api(frame, boxes, ids)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame = cv2.resize(rgb_frame, (640, 360))

        frame_dict[frame_index] = rgb_frame

        # Giữ tối đa 20 frame
        if len(frame_dict) > 20:
            for i in sorted(frame_dict.keys())[:len(frame_dict)-20]:
                frame_dict.pop(i)

        # Lấy frame index cao nhất
        if frame_dict:
            latest_index = max(frame_dict.keys())
            latest_frame = frame_dict.pop(latest_index)
            if frame_buffers[cid].full():
                try:
                    frame_buffers[cid].get_nowait()
                except queue.Empty:
                    pass
            frame_buffers[cid].put(latest_frame)

    consumer.start(handle_frame)

# ========= 5. Convert MongoDB data to DataFrame =========
def json_to_dataframe(data):
    if not data:
        return pd.DataFrame(columns=["Tên", "Vòng"])
    return pd.DataFrame([{"Tên": item.get("name",""), "Vòng": item.get("laps","")} for item in data])

# ========= 6. Gradio stream =========
def stream_ui(path1, path2, path3, path4):
    sources = {1: path1, 2: path2, 3: path3, 4: path4}
    last_frames = {cid: None for cid in CAM_IDS}

    # start producer threads (1 producer / camera)
    for cid, src in sources.items():
        if not src:
            continue
        if not any(t.name == f"producer-{cid}" for t in threading.enumerate()):
            t = threading.Thread(
                target=video_worker,
                args=(src, cid, producers[cid]),  # mỗi cam dùng producer riêng
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

    # ⏳ chờ ít nhất 1 frame từ tất cả camera
    while any(last_frames[cid] is None for cid in CAM_IDS):
        for cid in CAM_IDS:
            try:
                frame = frame_buffers[cid].get(timeout=0.1)
                last_frames[cid] = frame
            except queue.Empty:
                pass
        time.sleep(0.01)

    # 🔄 vòng lặp chính (~15-20 FPS)
    while True:
        frames = []
        for cid in CAM_IDS:
            try:
                frame = frame_buffers[cid].get(timeout=0.05)
                last_frames[cid] = frame
            except queue.Empty:
                frame = last_frames[cid]
            frames.append(frame)

        try:
            server_json = mongo_db.find_all("laps_db") or {}
        except Exception as e:
            logger.error(f"MongoDB error: {e}")
            server_json = {}

        server_df = json_to_dataframe(server_json)
        yield (*frames, server_df)
        time.sleep(FRAME_INTERVAL)

# ========= 7. Gradio UI =========
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
