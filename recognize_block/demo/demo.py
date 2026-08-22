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
    TRACK_RETRY_INTERVAL_SEC,
    TRACK_MAX_RETRY,
    TRACK_RETRY_GROWTH_FACTOR,
    MIN_SEARCH_BOX_AREA,
)
import json
from src.engine.engine import draw_target
import pandas as pd
import redis
from src.database.sql_model import PostgresHandler
from urllib.parse import quote_plus
from datetime import datetime
import asyncio
import csv
from pathlib import Path
import threading

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


def append_csv_row(csv_path, header, row):
    file_path = Path(csv_path)
    file_exists = file_path.exists()

    with file_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(header)

        writer.writerow(row)


def merge_frame_metrics_csv(cid):
    producer_file = Path(f"producer_{cid}_frames.csv")
    consumer_file = Path(f"consumer_{cid}_frames.csv")
    output_file = Path(f"frame_{cid}_final_metrics.csv")

    producer_rows = {}

    if producer_file.exists():
        with producer_file.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                frame_id = int(row["frame_id"])
                producer_rows[frame_id] = {
                    "frame_id": frame_id,
                    "time_seconds": float(row["producer_time_sec"]),
                    "status": row["status"],
                }

    if consumer_file.exists():
        with consumer_file.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                frame_id = int(row["frame_id"])
                total_time_sec = float(row["total_time_sec"])

                producer_rows[frame_id] = {
                    "frame_id": frame_id,
                    "time_seconds": total_time_sec,
                    "status": row["status"],
                }

    rows = sorted(producer_rows.values(), key=lambda x: x["frame_id"])

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "frame_id",
                "time_seconds",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"[Metric-{cid}] exported final csv: {output_file}")


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
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    else:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


    if not cap.isOpened():
        logger.error(f"[Producer-{cid}] Cannot open video {video_path}")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    logger.info(f"[Producer-{cid}] Video FPS = {video_fps}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    call_zone = [
        int(w * CALL_ZONE_X1_RATIO),
        int(h * CALL_ZONE_Y1_RATIO),
        int(w * CALL_ZONE_X2_RATIO),
        int(h * CALL_ZONE_Y2_RATIO),
    ]

    latest_frame_data = {
        "frame_id": -1,
        "frame": None,
        "captured_at_ms": 0,
    }

    latest_lock = threading.Lock()
    stop_event = threading.Event()

    def camera_reader_loop():
        frame_id = 0
        frame_interval = 1.0 / video_fps if video_fps > 0 else 1.0 / 30.0

        while not stop_event.is_set():
            read_start = time.time()

            ret, frame = cap.read()

            if not ret:
                logger.warning(f"[Producer-{cid}] camera read failed or end of stream")
                stop_event.set()
                break

            captured_at_ms = int(time.time() * 1000)

            with latest_lock:
                latest_frame_data["frame_id"] = frame_id
                latest_frame_data["frame"] = frame
                latest_frame_data["captured_at_ms"] = captured_at_ms

            frame_id += 1

            # Với video file thì sleep để giả lập realtime.
            # Với RTSP thật thì có thể bỏ sleep, nhưng giữ cũng không ảnh hưởng nhiều.
            if mode != "rtsp":
                elapsed = time.time() - read_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    reader_thread = threading.Thread(
        target=camera_reader_loop,
        daemon=True,
    )
    reader_thread.start()

    track_states = {}

    def box_area(box):
        x1, y1, x2, y2 = box
        return max(0, x2 - x1) * max(0, y2 - y1)

    def cleanup_track_states(now_ts: float):
        expired_track_ids = [
            track_id
            for track_id, state in track_states.items()
            if now_ts - state["last_seen_ts"] > TRACK_MEMORY_TTL_SEC
        ]

        for track_id in expired_track_ids:
            track_states.pop(track_id, None)

        if expired_track_ids:
            logger.debug(
                f"[Producer-{cid}] cleaned {len(expired_track_ids)} expired track(s): {expired_track_ids}"
            )

    last_processed_frame_id = -1

    try:
        while not stop_event.is_set():
            with latest_lock:
                frame_id = latest_frame_data["frame_id"]
                frame = latest_frame_data["frame"].copy() if latest_frame_data["frame"] is not None else None
                frame_start_ms = latest_frame_data["captured_at_ms"]

            if frame is None:
                time.sleep(0.001)
                continue

            if frame_id == last_processed_frame_id:
                time.sleep(0.001)
                continue

            last_processed_frame_id = frame_id

            frame_status = "no_person_or_not_sent"
            # frame_process_start = time.perf_counter()

            t0 = time.perf_counter()
            track_ids, boxes, _ = tracker.detect_frame(
                frame,
                call_zone_xyxy=call_zone,
                min_overlap_ratio=CALL_ZONE_MIN_OVERLAP_RATIO,
            )
            detect_time = time.perf_counter() - t0

            logger.info(
                f"[Producer-{cid}] frame={frame_id}, "
                f"detect_time={detect_time:.3f}s, track_ids={len(track_ids)}"
            )

            now_seen_ts = time.time()
            cleanup_track_states(now_seen_ts)

            send_track_ids = []
            send_boxes = []

            for track_id, box in zip(track_ids, boxes):
                area = box_area(box)

                state = track_states.get(track_id)
                if state is None:
                    state = {
                        "last_seen_ts": now_seen_ts,
                        "last_sent_ts": 0.0,
                        "retry_count": 0,
                        "best_sent_area": 0,
                    }
                    track_states[track_id] = state

                state["last_seen_ts"] = now_seen_ts

                if area < MIN_SEARCH_BOX_AREA:
                    logger.debug(
                        f"[Producer-{cid}] skip small box track_id={track_id}, "
                        f"area={area}, frame={frame_id}"
                    )
                    continue

                should_send = False

                if state["retry_count"] == 0:
                    should_send = True
                else:
                    # Nếu bạn đã bỏ TRACK_RETRY_INTERVAL_SEC và TRACK_MAX_RETRY,
                    # có thể đổi block này thành: should_send = True
                    enough_wait = (
                        now_seen_ts - state["last_sent_ts"]
                    ) >= TRACK_RETRY_INTERVAL_SEC

                    under_retry_limit = state["retry_count"] < TRACK_MAX_RETRY

                    # if enough_wait and under_retry_limit:
                    should_send = True

                if not should_send:
                    logger.debug(
                        f"[Producer-{cid}] hold track_id={track_id}, frame={frame_id}, "
                        f"area={area}, retry_count={state['retry_count']}, "
                        f"best_sent_area={state['best_sent_area']}"
                    )
                    continue

                send_track_ids.append(track_id)
                send_boxes.append(box)

            logger.info(
                f"[Producer-{cid}] frame={frame_id}, "
                f"raw_track_ids={track_ids}, send_track_ids={send_track_ids}"
            )

            if send_track_ids:
                captured_at_ms = int(time.time() * 1000)

                headers = [
                    ("frame_start_ms", str(frame_start_ms).encode()),
                    ("timestamp_ms", str(captured_at_ms).encode()),
                    ("frame_id", str(frame_id).encode()),
                    ("person_ids", json.dumps(send_track_ids).encode()),
                    ("bboxes", json.dumps(send_boxes).encode()),
                ]

                logger.warning(
                    f"[Producer-{cid}] WILL_ENQUEUE frame={frame_id}, "
                    f"send_track_ids={send_track_ids}"
                )

                sent = producer.send_frame(cid, frame, headers=headers)

                if sent:
                    frame_status = "sent_to_kafka"

                    sent_track_id_set = set(send_track_ids)
                    for track_id, box in zip(track_ids, boxes):
                        if track_id not in sent_track_id_set:
                            continue

                        state = track_states.get(track_id)
                        if state is None:
                            continue

                        area = box_area(box)
                        state["last_sent_ts"] = now_seen_ts
                        state["retry_count"] += 1
                        state["best_sent_area"] = max(state["best_sent_area"], area)
                else:
                    frame_status = "send_failed"
                    logger.warning(f"[Producer-{cid}] failed to enqueue frame={frame_id}")

                logger.warning(
                    f"[Producer-{cid}] ENQUEUE_RESULT frame={frame_id}, sent={sent}"
                )
            else:
                logger.debug(f"[Producer-{cid}] no eligible track to send at frame={frame_id}")

            frame_end_ms = int(time.time() * 1000)
            time_ms = frame_end_ms - frame_start_ms if frame_start_ms > 0 else -1

            append_csv_row(
                csv_path=f"producer_{cid}_frames.csv",
                header=[
                    "frame_id",
                    "start_ms",
                    "end_ms",
                    "time_ms",
                    "status",
                ],
                row=[
                    frame_id,
                    frame_start_ms,
                    frame_end_ms,
                    time_ms,
                    frame_status,
                ],
            )

    except Exception as e:
        logger.exception(f"[Producer-{cid}] crashed: {e}")

    finally:
        stop_event.set()

        try:
            reader_thread.join(timeout=2)
        except Exception:
            logger.exception(f"[Producer-{cid}] failed to join reader thread")

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
        worker_concurrency=1,
        max_pending_messages=10,
        drop_oldest_on_full=DROP_OLDEST_FRAME,
        stats_file_path=f'cam_{cid}_consumer_stats.txt',
        stats_flush_interval=5.0,
    )

    api = APIHandler(
        evaluator=setup_eval,
    )

    logger.info(f"[Consumer-{cid}] started")
    metric_csv_lock = asyncio.Lock()
    async def handle_frame(msg):
        frame_id = -1
        person_ids = []
        frame_start_ms = 0
        consumer_start_perf = time.perf_counter()

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

            frame_start_ms_raw = hdrs.get("frame_start_ms", b"0").decode()
            frame_start_ms = int(frame_start_ms_raw) if frame_start_ms_raw else 0

            timestamp_ms_raw = hdrs.get("timestamp_ms", b"0").decode()
            timestamp = int(timestamp_ms_raw) if timestamp_ms_raw else 0

            logger.info(
                f"[Consumer-{cid}] frame={frame_id}, persons={len(person_ids)}"
            )

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

            status = "processed"

        except Exception:
            status = "consumer_error"
            logger.exception(f"[Consumer-{cid}] error")

        finally:
            consumer_end_ms = time.time_ns() // 1_000_000
            consumer_time_sec = time.perf_counter() - consumer_start_perf

            if frame_start_ms > 0:
                total_time_sec = (consumer_end_ms - frame_start_ms) / 1000
            else:
                total_time_sec = -1

            async with metric_csv_lock:
                append_csv_row(
                    csv_path=f"consumer_{cid}_frames.csv",
                    header=[
                        "frame_id",
                        "consumer_time_sec",
                        "total_time_sec",
                        "status",
                    ],
                    row=[
                        frame_id,
                        round(consumer_time_sec, 6),
                        round(total_time_sec, 6),
                        status,
                    ],
                )

            logger.info(
                f"[Consumer-{cid}] finished processing frame={frame_id} "
                f"consumer_time={consumer_time_sec:.3f}s "
                f"total_time={total_time_sec:.3f}s "
                f"status={status}"
            )
    await consumer.start(handle_frame)


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
            args=(cid, video_sources[str(cid)], start_barrier, "camera"),
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
    finally:
        logger.info("📊 Merging frame metrics CSV...")

        for cid in CAM_IDS:
            try:
                merge_frame_metrics_csv(cid)
            except Exception:
                logger.exception(f"[Metric-{cid}] failed to merge csv")

        logger.info("✅ Merge frame metrics CSV finished")

if __name__ == "__main__":
    main()