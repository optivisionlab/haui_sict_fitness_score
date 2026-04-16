import cv2
import numpy as np
import multiprocessing as mp
import time
from loguru import logger
from ultralytics import YOLO
from confluent_kafka.admin import AdminClient, NewTopic

from src.engine.detect import SimpleTracker, APIHandler
from src.engine.score import SetUpEvaluate
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.config.config import (
    KAFKA_SERVERS,
    TEST_MODE,
    YOLO_MODEL_PATH,
    CAM_IDS,
    KAFKA_TOPIC_TEMPLATE,
    START_BARRIER_TIMEOUT_SEC,
    EVAL_CONFIG,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    POSTGRE_DSN,
    CALL_ZONE_X1_RATIO,
    CALL_ZONE_Y1_RATIO,
    CALL_ZONE_X2_RATIO,
    CALL_ZONE_Y2_RATIO,
    CALL_ZONE_MIN_OVERLAP_RATIO,
    CAMERA_SOURCE_URLS,
    DROP_OLDEST_FRAME,
    YOLO_TRACKER_CONFIG,
    TRACK_MEMORY_TTL_SEC,
)
import json
from src.engine.engine import draw_target
import pandas as pd
import redis
from src.database.sql_model import PostgresHandler
from urllib.parse import quote_plus
from datetime import datetime
import asyncio


# ================== CONFIG ==================
MODEL_PATH = YOLO_MODEL_PATH

TOPIC_TEMPLATE = KAFKA_TOPIC_TEMPLATE

# ================== REDIS ==================
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)

try:
    redis_client.ping()
    print("✅ Kết nối Redis thành công!")
except redis.ConnectionError as e:
    print("❌ Kết nối Redis thất bại:", e)


# ================== POSTGRES ==================
pg_handler = PostgresHandler(POSTGRE_DSN)


# ================== KAFKA CONFIG ==================
producer_conf = {
    "bootstrap.servers": KAFKA_SERVERS,  # hoặc list broker
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
logger.info(f"Kafka Producer Config: {producer_conf}")
logger.info(f"Kafka Consumer Config: {consumer_conf}")

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

    tracker = SimpleTracker(
        detection_model=model,
        cam_id=cid,
        tracker_config=YOLO_TRACKER_CONFIG,
    )

    _wait_start_barrier(cid, start_barrier, "Producer")
    logger.info(f"[Producer-{cid}] started")

    topic = TOPIC_TEMPLATE.format(cid=cid)

    producer = KafkaFrameProducer(
        producer_conf,
        topic_template=topic,
        jpeg_quality=80,
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

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    logger.info(f"[Producer-{cid}] Video FPS = {video_fps}")

    frame_interval = 1.0 / video_fps
    TARGET_DETECT_FPS = video_fps
    frame_step = max(1, int(round(video_fps / TARGET_DETECT_FPS)))

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    call_zone = [
        int(w * CALL_ZONE_X1_RATIO),
        int(h * CALL_ZONE_Y1_RATIO),
        int(w * CALL_ZONE_X2_RATIO),
        int(h * CALL_ZONE_Y2_RATIO),
    ]

    frame_count = 0
    next_frame_time = time.time()

    # memory dedup for this camera only: {track_id: last_seen_ts}
    seen_tracks = {}
    def cleanup_seen_tracks(now_ts: float):
        expired_track_ids = [
            track_id
            for track_id, last_seen_ts in seen_tracks.items()
            if now_ts - last_seen_ts > TRACK_MEMORY_TTL_SEC
        ]
        for track_id in expired_track_ids:
            seen_tracks.pop(track_id, None)

        if expired_track_ids:
            logger.debug(
                f"[Producer-{cid}] cleaned {len(expired_track_ids)} expired track(s): {expired_track_ids}"
            )

    try:
        while True:
            now = time.time()

            if now < next_frame_time:
                time.sleep(next_frame_time - now)

            next_frame_time += frame_interval

            ret, frame = cap.read()

            if not ret:
                logger.info(f"[Producer-{cid}] End of video")
                break

            if frame_count % frame_step == 0:
                t0 = time.perf_counter()
                track_ids, boxes, _ = tracker.detect_frame(
                    frame,
                    call_zone_xyxy=call_zone,
                    min_overlap_ratio=CALL_ZONE_MIN_OVERLAP_RATIO,
                )
                detect_time = time.perf_counter() - t0

                logger.info(
                    f"[Producer-{cid}] frame={frame_count}, "
                    f"detect_time={detect_time:.3f}s, track_ids={len(track_ids)}"
                )

                now_seen_ts = time.time()
                cleanup_seen_tracks(now_seen_ts)

                new_track_ids = []
                new_boxes = []
                logger.info("seen_tracks: {}", seen_tracks)
                for track_id, box in zip(track_ids, boxes):
                    if track_id in seen_tracks:
                        seen_tracks[track_id] = now_seen_ts
                        logger.debug(
                            f"[Producer-{cid}] skip duplicated track_id={track_id} frame={frame_count}"
                        )
                        continue

                    seen_tracks[track_id] = now_seen_ts
                    new_track_ids.append(track_id)
                    new_boxes.append(box)

                if new_track_ids:
                    captured_at_ms = time.time_ns() // 1_000_000

                    headers = [
                        ("timestamp_ms", str(captured_at_ms).encode()),
                        ("frame_id", str(frame_count).encode()),
                        # giữ nguyên key header để downstream không phải sửa
                        ("person_ids", json.dumps(new_track_ids).encode()),
                        ("bboxes", json.dumps(new_boxes).encode()),
                    ]

                    sent = producer.send_frame(cid, frame, headers=headers)
                    if sent:
                        logger.info(f"[Producer-{cid}] enqueued frame={frame_count} with {len(new_track_ids)} new track(s)")
                    if not sent:
                        logger.warning(f"[Producer-{cid}] failed to enqueue frame={frame_count}")
                else:
                    logger.debug(f"[Producer-{cid}] no new track to send at frame={frame_count}")

            frame_count += 1

    except Exception as e:
        logger.exception(f"[Producer-{cid}] crashed: {e}")

    finally:
        cap.release()
        producer.flush(5)
        logger.info(f"[Producer-{cid}] finished")


# ================== CONSUMER (1 per camera) ==================
async def consumer_worker(cid: int):
    topic = TOPIC_TEMPLATE.format(cid=cid)
    logger.info(f"[Consumer-{cid}] DROP_OLDEST_FRAME={DROP_OLDEST_FRAME}")
    setup_eval = SetUpEvaluate(
        id_run_process=CAM_IDS,
        redis_client=redis_client,
        pg_handler=pg_handler,
        test_mode=TEST_MODE,
        config=EVAL_CONFIG
    )

    consumer = KafkaFrameConsumer(
        consumer_conf,
        topic,
        group_id=f"group-{topic}",
        # Realtime mode: allow parallel processing but keep safe-commit ordering.
        worker_concurrency=2,
        max_pending_messages=16,
        drop_oldest_on_full=DROP_OLDEST_FRAME,
        stats_file_path=f'cam_{cid}_consumer_stats.txt',
        stats_flush_interval=5.0,
    )

    api = APIHandler(
        evaluator=setup_eval,
    )

    logger.info(f"[Consumer-{cid}] started")

    async def handle_frame(msg):
        try:
            start_time = time.perf_counter()
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
            import asyncio
            logger.info(
                f"[Consumer-{cid}] task={id(asyncio.current_task())} start frame={frame_id}"
            )
            await api.process(
                cid,
                frame,
                bboxes,
                person_ids,
                timestamp=timestamp,
            )
            logger.info(
                f"[Consumer-{cid}] task={id(asyncio.current_task())} done frame={frame_id}"
            )
        except Exception:
            logger.exception(f"[Consumer-{cid}] error")
        finally:
            logger.info(f"[Consumer-{cid}] finished processing frame={frame_id} in {time.perf_counter() - start_time:.3f}s")
            with open(f"consumer_{cid}_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} | frame={frame_id} | persons={len(person_ids)} | process_time={(time.perf_counter() - start_time):.3f}s\n")

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

    video_sources = CAMERA_SOURCE_URLS
    missing_cam_ids = [cid for cid in CAM_IDS if str(cid) not in video_sources]
    if missing_cam_ids:
        raise ValueError(f"Missing CAMERA_SOURCE_URLS for cam ids: {missing_cam_ids}")

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
            args=(cid, video_sources[str(cid)], start_barrier, "rtsp"),
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