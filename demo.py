import cv2
import numpy as np
import multiprocessing as mp
import time
from loguru import logger
from ultralytics import YOLO
from confluent_kafka.admin import AdminClient, NewTopic

from src.engine.detect import SimpleTracker, APIHandler
from src.engine.score import GlobalEvaluator, SetUpEvaluate
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.config.config import KAFKA_SERVERS, MONGO_LAPS_COLLECTION
import json
from src.engine.engine import draw_target
import queue
# import gradio as gr
import threading
import pandas as pd
# from pymongo import MongoClient
# from src.database.mongo import MongoDBManager
import redis
from src.database.sql_model import PostgresHandler
from urllib.parse import quote_plus
from datetime import datetime


# ================== CONFIG ==================
MODEL_PATH = "weights\yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]   # camera id
# CAM_IDS = [1]   # camera id

TOPIC_TEMPLATE = "camera-{cid}"

# Kết nối Redis
redis_client = redis.Redis(
    host='10.100.200.119',
    port=6379,
    db=0,  # mặc định
    password='optivisionlab',
    decode_responses=True  # để trả về string thay vì bytes
)

try:
    redis_client.ping()
    print("✅ Kết nối Redis thành công!")
except redis.ConnectionError as e:
    print("❌ Kết nối Redis thất bại:", e)

# Kết nối PostgreSQL
user = "labelstudio"
password = "Admin@221b"
host = "10.100.200.119"
port = 5555
database = "fitness_db"

encoded_password = quote_plus(password)
# URL kết nối PostgreSQL
DB_URL = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"
pg_handler = PostgresHandler(DB_URL)


producer_conf = {
    "bootstrap.servers": "10.100.200.119:9098",   # hoặc list broker
    "acks": "1",                             # nhanh hơn "all"
    "message.timeout.ms": 60000,             # timeout gửi 60s
    "delivery.timeout.ms": 120000,           # timeout delivery 120s
    "socket.timeout.ms": 60000,
    "request.timeout.ms": 30000,
    "retries": 5,
    "max.in.flight.requests.per.connection": 5,
    "batch.num.messages": 1000,
    "linger.ms": 10,
    "compression.type": "lz4",               # giảm size gửi
    "message.max.bytes": 10485760,            # 10MB (nếu frame lớn)
    "queue.buffering.max.messages": 200000,
    "queue.buffering.max.kbytes": 51200,   # 500MB
}

consumer_conf = {"bootstrap.servers": KAFKA_SERVERS}

# tạo queue cho gradio

# Giả sử bạn có danh sách các camera id
# Tạo 1 hàng đợi (queue) cho mỗi camera
# ================== KAFKA UTILS ==================
def create_topics(cam_ids):
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVERS})
    topics_list = [
        NewTopic(TOPIC_TEMPLATE.format(cid=cid), num_partitions=1, replication_factor=1)
        for cid in cam_ids
    ]
    fs = admin.create_topics(topics_list)
    for t, f in fs.items():
        try:
            f.result()
            logger.info(f"✅ Created topic {t}")
        except Exception as e:
            logger.warning(f"⚠️ Topic {t} may already exist: {e}")


lap_evaluator = GlobalEvaluator(id_run_process=CAM_IDS, redis_client=redis_client, pg_handler=pg_handler)



# ================== PRODUCER (Tracker Process) ==================
def tracker_producer_worker(cid: int, video_path: str, mode='rtsp'):
    model = YOLO(MODEL_PATH)
    logger.info(f"[Producer-{cid}] start with video={video_path}")

    topic = TOPIC_TEMPLATE.format(cid=cid)
    producer = KafkaFrameProducer(producer_conf, topic_template=topic, jpeg_quality=60, drop_on_full=True, max_backoff_sec=5.0)

    tracker = SimpleTracker(detection_model=model, cam_id=cid)
    if mode == 'rtsp':
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_interval = 1.0 / fps
    frame_index = 0
    stop_frame = int(fps)
    # === Tạo VideoWriter để ghi file output ===
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # hoặc 'XVID'
    out_path = f"output_cam{cid}.mp4"
    out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    try:
        batch_size = 1
        frames_batch = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_index += 1
            if frame_index % stop_frame != 0:
                # xử lý frame
                continue
            frames_batch.append((frame_index, frame))

            # detect theo batch
            if len(frames_batch) >= batch_size:
                idxs, imgs = zip(*frames_batch)
                results = tracker.detect_batch(list(imgs))

                for idx, (ids, boxes, frame) in zip(idxs, results):
                    copy_frame = frame.copy()

                    if ids:
                        for uid, box in zip(ids, boxes):
                            copy_frame = draw_target(copy_frame, uid, box, name=f"Person", color=(0, 255, 0), thickness=2)
                    
                    out.write(copy_frame)  # Ghi frame vào file video

                    if ids:  # có người
                        headers=[
                            ("timestamp", str(datetime.now().strftime('%Y/%m/%d/%H/%M/%S')).encode()),
                            ("frame_id", str(idx).encode()),
                            ("person_ids", json.dumps(ids).encode()),          # [1,2,3] -> b'[1, 2, 3]'
                            ("bboxes", json.dumps(boxes).encode())             # [[x1,y1,x2,y2], ...]
                        ]
                        sent = producer.send_frame(
                            cid,
                            frame,
                            headers=headers
                        )
                        time.sleep(0.01)  # tránh gửi quá nhanh
                        if not sent:
                            logger.exception(f"[Producer-{cid}] failed to send frame {idx}")
                        else:
                            logger.info(f"[Producer-{cid}] sent frame {idx} with {len(ids)} persons")
                        #   copy frame gốc
                frames_batch.clear()
            time.sleep(frame_interval)

    finally:
        cap.release()
        out.release()
        producer.flush(5)
        logger.info(f"[Producer-{cid}] finished")


# ================== CONSUMER (1 per camera) ==================
def consumer_worker(cid: int):
    topic = TOPIC_TEMPLATE.format(cid=cid)
    setup_eval = SetUpEvaluate(id_run_process=CAM_IDS, redis_client=redis_client, pg_handler=pg_handler, test_mode=True)
    consumer = KafkaFrameConsumer(consumer_conf, topic, group_id=f"group-{topic}")
    api = APIHandler(evaluator=setup_eval, lap_update=lap_evaluator)

    def handle_frame(msg):
        try:
            nparr = np.frombuffer(msg.value(), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            logger.info(frame.shape)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            hdrs = dict(msg.headers() or [])
            # headers lưu dạng bytes, cần decode + json.loads
            person_ids = json.loads(hdrs.get("person_ids", b"[]").decode())
            bboxes = json.loads(hdrs.get("bboxes", b"[]").decode())
            frame_id = int(hdrs.get("frame_id", b"-1").decode())
            time_stamp = hdrs.get("timestamp", b"").decode()
            logger.info(f"person_ids: {person_ids}, bboxes: {bboxes}, frame_id: {frame_id}")
            api.process(cid, frame, bboxes, person_ids, timestamp=time_stamp)
            # 👉 ở đây bạn có thể hiển thị frame, push UI, ghi DB, v.v.
        except Exception as e:
            logger.exception(f"[Consumer-{cid}] error: {e}")

    consumer.start(handle_frame)


# ================== MAIN ==================

# main với truyền source test
def main():
    create_topics(CAM_IDS)

    video_sources = {
        1: r"D:\NCKH_Cham_diem_the_duc\assets\test\6_12\1231.mp4",
        2: r"D:\NCKH_Cham_diem_the_duc\assets\test\6_12\IMG_1550.MOV",
        3: r"D:\NCKH_Cham_diem_the_duc\assets\test\6_12\IMG_0503.MOV",
        4: r"D:\NCKH_Cham_diem_the_duc\assets\test\6_12\VID_20251206_105125.mp4",
    }

    ctx = mp.get_context("spawn")
    progress = ctx.Manager().dict({cid: 0 for cid in CAM_IDS})
    processes = []
    # start producers
    for cid in CAM_IDS:
        p = ctx.Process(target=tracker_producer_worker, args=(cid, video_sources[cid]), daemon=True)
        p.start()
        processes.append(p)

    # start consumers
    for cid in CAM_IDS:
        p = ctx.Process(target=consumer_worker, args=(cid,), daemon=True)
        p.start()
        processes.append(p)

    # join all
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping all processes...")
        for p in processes:
            p.terminate()


if __name__ == "__main__":
    main()
