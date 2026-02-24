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
from src.config.config import KAFKA_SERVERS, MONGO_LAPS_COLLECTION, TEST_MODE
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
MODEL_PATH = "weights\\yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]   # camera id
# CAM_IDS = [1]   # camera id

TOPIC_TEMPLATE = "camera-{cid}"


# ================== REDIS ==================
redis_client = redis.Redis(
    host="10.100.200.119",
    port=6379,
    db=0,  # mặc định
    password="optivisionlab",
    decode_responses=True,  # để trả về string thay vì bytes
)

try:
    redis_client.ping()
    print("✅ Kết nối Redis thành công!")
except redis.ConnectionError as e:
    print("❌ Kết nối Redis thất bại:", e)


# ================== POSTGRES ==================
user = "labelstudio"
password = "Admin@221b"
host = "10.100.200.119"
port = 5555
database = "fitness_db"

encoded_password = quote_plus(password)

# URL kết nối PostgreSQL
DB_URL = (
    f"postgresql+psycopg2://{user}:{encoded_password}"
    f"@{host}:{port}/{database}"
)

pg_handler = PostgresHandler(DB_URL)


# ================== KAFKA CONFIG ==================
producer_conf = {
    "bootstrap.servers": "10.100.200.119:9098",  # hoặc list broker
    "acks": "1",  # nhanh hơn "all"
    "message.timeout.ms": 60000,  # timeout gửi 60s
    "delivery.timeout.ms": 120000,  # timeout delivery 120s
    "socket.timeout.ms": 60000,
    "request.timeout.ms": 30000,
    "retries": 5,
    "max.in.flight.requests.per.connection": 5,
    "batch.num.messages": 1000,
    "linger.ms": 10,
    "compression.type": "lz4",  # giảm size gửi
    "message.max.bytes": 10485760,  # 10MB (nếu frame lớn)
    "queue.buffering.max.messages": 200000,
    "queue.buffering.max.kbytes": 51200,  # 500MB
}

consumer_conf = {"bootstrap.servers": KAFKA_SERVERS}


# ================== KAFKA UTILS ==================
def create_topics(cam_ids):
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVERS})

    topics_list = [
        NewTopic(
            TOPIC_TEMPLATE.format(cid=cid),
            num_partitions=1,
            replication_factor=1,
        )
        for cid in cam_ids
    ]

    fs = admin.create_topics(topics_list)

    for t, f in fs.items():
        try:
            f.result()
            logger.info(f"✅ Created topic {t}")
        except Exception as e:
            logger.warning(f"⚠️ Topic {t} may already exist: {e}")


def log_detect_time(
    cam_id,
    frame_id,
    detect_time,
    num_ids,
    logfile=None,
):
    if logfile is None:
        logfile = f"detect_time_cam{cam_id}.log"

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{ts} | cam={cam_id} | frame={frame_id} | "
        f"{detect_time*1000:.2f} ms | ids={num_ids}\n"
    )

    with open(logfile, "a", encoding="utf-8") as f:
        f.write(line)


# ================== PRODUCER (Tracker Process) ==================
def tracker_producer_worker(cid, video_path, start_barrier, mode="rtsp"):
    logger.info(f"[Producer-{cid}] loading model...")
    model = YOLO(MODEL_PATH)

    tracker = SimpleTracker(detection_model=model, cam_id=cid)

    logger.info(f"[Producer-{cid}] ready, waiting at barrier...")
    start_barrier.wait()  # 🚦 đồng bộ START
    logger.info(f"[Producer-{cid}] started")

    topic = TOPIC_TEMPLATE.format(cid=cid)

    producer = KafkaFrameProducer(
        producer_conf,
        topic_template=topic,
        jpeg_quality=60,
        drop_on_full=True,
        max_backoff_sec=5.0,
    )

    if mode == "rtsp":
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        logger.error(f"[Producer-{cid}] Cannot open video {video_path}")
        return

    # ================= VIDEO INFO =================
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    logger.info(f"[Producer-{cid}] Video FPS = {video_fps}")

    frame_interval = 1.0 / video_fps
    sample_interval = 1.0
    frame_step = int(video_fps * sample_interval)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(
        f"output_cam{cid}.mp4",
        cv2.VideoWriter_fourcc(*"mp4v"),
        video_fps,
        (w, h),
    )

    frame_count = 0
    next_frame_time = time.time()

    try:
        while True:
            # ===== REAL-TIME SYNC =====
            now = time.time()

            if now < next_frame_time:
                time.sleep(next_frame_time - now)

            next_frame_time += frame_interval

            ret, frame = cap.read()

            if not ret:
                logger.info(f"[Producer-{cid}] End of video")
                break

            copy_frame = frame.copy()

            # ===== DETECT 1s / frame =====
            if frame_count % frame_step == 0:
                t0 = time.perf_counter()
                results = tracker.detect_batch([frame])
                detect_time = time.perf_counter() - t0

                ids, boxes, _ = results[0]

                log_detect_time(
                    cam_id=cid,
                    frame_id=frame_count,
                    detect_time=detect_time,
                    num_ids=len(ids),
                )

                logger.info(
                    f"[Producer-{cid}] frame={frame_count}, "
                    f"detect_time={detect_time:.3f}s, ids={len(ids)}"
                )

                if ids:
                    for uid, box in zip(ids, boxes):
                        copy_frame = draw_target(
                            copy_frame,
                            uid,
                            box,
                            name="Person",
                            color=(0, 255, 0),
                            thickness=2,
                        )

                    headers = [
                        (
                            "timestamp",
                            datetime.now()
                            .strftime("%Y/%m/%d/%H/%M/%S")
                            .encode(),
                        ),
                        ("frame_id", str(frame_count).encode()),
                        ("person_ids", json.dumps(ids).encode()),
                        ("bboxes", json.dumps(boxes).encode()),
                    ]

                    producer.send_frame(cid, frame, headers=headers)

            # ===== ALWAYS WRITE FULL VIDEO =====
            out.write(copy_frame)
            frame_count += 1

    except Exception as e:
        logger.exception(f"[Producer-{cid}] crashed: {e}")

    finally:
        cap.release()
        out.release()
        producer.flush(5)
        logger.info(f"[Producer-{cid}] finished")


# ================== CONSUMER (1 per camera) ==================
def consumer_worker(cid: int, start_barrier):
    topic = TOPIC_TEMPLATE.format(cid=cid)

    setup_eval = SetUpEvaluate(
        id_run_process=CAM_IDS,
        redis_client=redis_client,
        pg_handler=pg_handler,
        test_mode=TEST_MODE,
    )

    consumer = KafkaFrameConsumer(
        consumer_conf,
        topic,
        group_id=f"group-{topic}",
    )

    api = APIHandler(
        evaluator=setup_eval,
    )

    logger.info(f"[Consumer-{cid}] ready, waiting at barrier...")
    start_barrier.wait()
    logger.info(f"[Consumer-{cid}] started")

    def handle_frame(msg):
        try:
            nparr = np.frombuffer(msg.value(), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            hdrs = dict(msg.headers() or [])

            person_ids = json.loads(
                hdrs.get("person_ids", b"[]").decode()
            )
            bboxes = json.loads(
                hdrs.get("bboxes", b"[]").decode()
            )
            frame_id = int(
                hdrs.get("frame_id", b"-1").decode()
            )
            time_stamp = hdrs.get(
                "timestamp", b""
            ).decode()

            logger.info(
                f"[Consumer-{cid}] frame={frame_id}, "
                f"persons={len(person_ids)}"
            )

            api.process(
                cid,
                frame,
                bboxes,
                person_ids,
                timestamp=time_stamp,
            )

        except Exception:
            logger.exception(f"[Consumer-{cid}] error")

    consumer.start(handle_frame)


# ================== MAIN ==================
def main():
    logger.info("🚀 Starting demo...")
    create_topics(CAM_IDS)

    video_sources = {
        1: r"D:\NCKH_Cham_diem_the_duc\1231.mp4",
        2: r"D:\NCKH_Cham_diem_the_duc\IMG_1550.MOV",
        3: r"D:\NCKH_Cham_diem_the_duc\0126.mp4",
        4: r"D:\NCKH_Cham_diem_the_duc\VID_20251206_105125.mp4",
    }

    ctx = mp.get_context("spawn")

    num_producers = len(CAM_IDS)
    num_consumers = len(CAM_IDS)

    # ===== BARRIER =====
    start_barrier = ctx.Barrier(num_producers + num_consumers)

    processes = []

    # ===== start producers =====
    for cid in CAM_IDS:
        p = ctx.Process(
            target=tracker_producer_worker,
            args=(cid, video_sources[cid], start_barrier),
            daemon=False,
        )
        p.start()
        processes.append(p)

    # ===== start consumers =====
    for cid in CAM_IDS:
        p = ctx.Process(
            target=consumer_worker,
            args=(cid, start_barrier),
            daemon=False,
        )
        p.start()
        processes.append(p)

    logger.info("🚦 Waiting for all processes to finish...")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping all processes...")
        for p in processes:
            p.terminate()
            p.join()


if __name__ == "__main__":
    main()