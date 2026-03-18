import cv2
import numpy as np
import multiprocessing as mp
import time
from loguru import logger
from ultralytics import YOLO
from confluent_kafka.admin import AdminClient, NewTopic

from src.engine.detect import SimpleTracker, APIHandler
from src.engine.score import EvalConfig, SetUpEvaluate
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.config.config import KAFKA_SERVERS, TEST_MODE
import json
from src.engine.engine import draw_target
import pandas as pd
import redis
from src.database.sql_model import PostgresHandler
from urllib.parse import quote_plus
from datetime import datetime
import asyncio


# ================== CONFIG ==================
MODEL_PATH = "weights\\yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]   # camera id
# CAM_IDS = [1]   # camera id

TOPIC_TEMPLATE = "camera-{cid}"
START_BARRIER_TIMEOUT_SEC = 30
UPLOAD_EACH_CHECKIN = False  # tắt upload proof trong hot path để ưu tiên realtime

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
    "queue.buffering.max.kbytes": 204800,  # 200MB
    "message.timeout.ms": 60000,

}

consumer_conf = {"bootstrap.servers": KAFKA_SERVERS}

CALL_ZONE_X1_RATIO = 0.0
CALL_ZONE_Y1_RATIO = 0.0
CALL_ZONE_X2_RATIO = 1.0
CALL_ZONE_Y2_RATIO = 0.5
CALL_ZONE_MIN_OVERLAP_RATIO = 0.8

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

def _wait_start_barrier(cid: int, start_barrier, role: str):
    logger.info(f"[{role}-{cid}] ready, waiting at barrier...")
    try:
        start_barrier.wait(timeout=START_BARRIER_TIMEOUT_SEC)
    except Exception as e:
        logger.exception(f"[{role}-{cid}] barrier wait failed: {e}")
        raise
    logger.info(f"[{role}-{cid}] released from barrier")


# ================== PRODUCER (Tracker Process) ==================
def tracker_producer_worker(cid, video_path, start_barrier, mode="rtsp"):
    logger.info(f"[Producer-{cid}] loading model...")
    model = YOLO(MODEL_PATH)

    tracker = SimpleTracker(detection_model=model, cam_id=cid)

    _wait_start_barrier(cid, start_barrier, "Producer")
    logger.info(f"[Producer-{cid}] started")

    topic = TOPIC_TEMPLATE.format(cid=cid)

    producer = KafkaFrameProducer(
        producer_conf,
        topic_template=topic,
        jpeg_quality=60,
        drop_on_full=False,
        max_backoff_sec=30,
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
    TARGET_DETECT_FPS = 6
    frame_step = max(1, int(round(video_fps / TARGET_DETECT_FPS)))

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    call_zone = [
        int(w * CALL_ZONE_X1_RATIO),
        int(h * CALL_ZONE_Y1_RATIO),
        int(w * CALL_ZONE_X2_RATIO),
        int(h * CALL_ZONE_Y2_RATIO),
    ]
    # out = cv2.VideoWriter(
    #     f"output_cam{cid}.mp4",
    #     cv2.VideoWriter_fourcc(*"mp4v"),
    #     video_fps,
    #     (w, h),
    # )

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

            if frame_count % frame_step == 0:
                t0 = time.perf_counter()
                ids, boxes, _  = tracker.detect_frame(frame, call_zone_xyxy=call_zone, min_overlap_ratio=CALL_ZONE_MIN_OVERLAP_RATIO)
                detect_time = time.perf_counter() - t0


                # log_detect_time(
                #     cam_id=cid,
                #     frame_id=frame_count,
                #     detect_time=detect_time,
                #     num_ids=len(ids),
                # )

                logger.info(
                    f"[Producer-{cid}] frame={frame_count}, "
                    f"detect_time={detect_time:.3f}s, ids={len(ids)}"
                )

                if ids:
                    captured_at_ms = time.time_ns() // 1_000_000
                    # for uid, box in zip(ids, boxes):
                    #     copy_frame = draw_target(
                    #         copy_frame,
                    #         uid,
                    #         box,
                    #         name="Person",
                    #         color=(0, 255, 0),
                    #         thickness=2,
                    #     )

                    headers = [
                        ("timestamp_ms", str(captured_at_ms).encode()),   # epoch seconds,
                        ("frame_id", str(frame_count).encode()),
                        ("person_ids", json.dumps(ids).encode()),
                        ("bboxes", json.dumps(boxes).encode()),
                    ]

                    sent = producer.send_frame(cid, frame, headers=headers)
                    if not sent:
                        logger.warning(f"[Producer-{cid}] failed to enqueue frame={frame_count}")

            # ===== ALWAYS WRITE FULL VIDEO =====
            # out.write(copy_frame)
            frame_count += 1

    except Exception as e:
        logger.exception(f"[Producer-{cid}] crashed: {e}")

    finally:
        cap.release()
        # out.release()
        producer.flush(5)
        logger.info(f"[Producer-{cid}] finished")


# ================== CONSUMER (1 per camera) ==================
async def consumer_worker(cid: int):
    topic = TOPIC_TEMPLATE.format(cid=cid)

    setup_eval = SetUpEvaluate(
        id_run_process=CAM_IDS,
        redis_client=redis_client,
        pg_handler=pg_handler,
        test_mode=TEST_MODE,
        config=EvalConfig(upload_each_checkin=UPLOAD_EACH_CHECKIN)
    )

    consumer = KafkaFrameConsumer(
        consumer_conf,
        topic,
        group_id=f"group-{topic}",
        # Realtime mode: allow parallel processing but keep safe-commit ordering.
        worker_concurrency=2,
        max_pending_messages=16,
        drop_oldest_on_full=True,
    )

    api = APIHandler(
        evaluator=setup_eval,
    )

    logger.info(f"[Consumer-{cid}] started")

    async def handle_frame(msg):
        try:
            nparr = np.frombuffer(msg.value(), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

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
            timestamp_ms_raw = hdrs.get("timestamp_ms", b"0").decode()
            timestamp = int(timestamp_ms_raw) if timestamp_ms_raw else 0 #miliseconds

            logger.info(
                f"[Consumer-{cid}] frame={frame_id}, persons={len(person_ids)}"
            )

            await api.process(
                cid,
                frame,
                bboxes,
                person_ids,
                timestamp=timestamp,
            )

        except Exception:
            logger.exception(f"[Consumer-{cid}] error")

    await consumer.start(handle_frame)


def consumer_worker_entry(cid: int, start_barrier):
    try:
        _wait_start_barrier(cid, start_barrier, "Consumer")
        asyncio.run(consumer_worker(cid))
    except Exception:
        logger.exception(f"[Consumer-{cid}] crashed before start")


# async consumer entry point for multiprocessing
def consumer_worker_entry(cid: int, start_barrier):
    try:
        _wait_start_barrier(cid, start_barrier, "Consumer")
        asyncio.run(consumer_worker(cid))
    except Exception:
        logger.exception(f"[Consumer-{cid}] crashed before start")


# ================== MAIN ==================
def main():
    logger.info("🚀 Starting demo...")
    create_topics(CAM_IDS)

    video_sources = {
        1: r"D:\haui_sict_fitness_score\data_test\0207 (1).mp4",
        2: r"D:\haui_sict_fitness_score\data_test\0207 (1)(1).mp4",
        3: r"D:\haui_sict_fitness_score\data_test\0207 (1)(2).mp4",
        4: r"D:\haui_sict_fitness_score\data_test\0207 (1)(3).mp4",
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
            target=consumer_worker_entry,
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