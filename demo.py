import cv2
import numpy as np
import multiprocessing as mp
import time
from loguru import logger
from ultralytics import YOLO
from confluent_kafka.admin import AdminClient, NewTopic

from src.tracking.detect import SimpleTracker
from src.engine.score import GlobalEvaluator
from src.kafka.kafka_produce import KafkaFrameProducer
from src.kafka.kafka_consumers import KafkaFrameConsumer
from src.config.config import KAFKA_SERVERS

# ================== CONFIG ==================
MODEL_PATH = "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/yolo11n.pt"
CAM_IDS = [1, 2, 3, 4]
TOPIC_TEMPLATE = "camera-{cid}"
model = YOLO(MODEL_PATH)
evaluator = GlobalEvaluator(id_run_process=CAM_IDS)

producer_conf = {
    'bootstrap.servers': KAFKA_SERVERS,
    'compression.type': 'lz4',
    'linger.ms': 10,
    'batch.num.messages': 100000,
    'message.max.bytes': 10000000,
}

consumer_conf = {"bootstrap.servers": KAFKA_SERVERS}


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


# ================== PRODUCER (Tracker Process) ==================
def tracker_producer_worker(cid: int, video_path: str):
    logger.info(f"[Producer-{cid}] start with video={video_path}")

    topic = TOPIC_TEMPLATE.format(cid=cid)
    producer = KafkaFrameProducer(producer_conf, topic_template=topic, jpeg_quality=70)

    tracker = SimpleTracker(model, cam_id=cid)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = 1.0 / fps
    frame_index = 0

    try:
        batch_size = 8
        frames_batch = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames_batch.append((frame_index, frame))
            frame_index += 1

            # detect theo batch
            if len(frames_batch) >= batch_size:
                idxs, imgs = zip(*frames_batch)
                results = tracker.detect_batch(list(imgs))

                for idx, (ids, boxes, frame) in zip(idxs, results):
                    if ids:  # có người
                        sent = producer.send_frame(
                            cid,
                            frame,
                        )
                        if not sent:
                            logger.warning(f"[Producer-{cid}] failed to send frame {idx}")
                        else:
                            logger.info(f"[Producer-{cid}] sent frame {idx} with {len(ids)} persons")

                frames_batch = []

            time.sleep(frame_interval)

    finally:
        cap.release()
        logger.info(f"[Producer-{cid}] finished")

frame_dict = {}
# ================== CONSUMER (1 per camera) ==================
def consumer_worker(cid: int):
    topic = TOPIC_TEMPLATE.format(cid=cid)
    consumer = KafkaFrameConsumer(consumer_conf, topic, group_id=f"group-{topic}")

    def handle_frame(msg):
        try:
            headers = dict(msg.headers() or [])
            nparr = np.frombuffer(msg.value(), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            logger.info(frame.shape)
            # 👉 ở đây bạn có thể hiển thị frame, push UI, ghi DB, v.v.
            frame_dict[cid] = frame
        except Exception as e:
            logger.error(f"[Consumer-{cid}] error: {e}")

    consumer.start(handle_frame)


# ================== MAIN ==================
def main():
    create_topics(CAM_IDS)

    video_sources = {
        1: "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/test/Chaylanmot.mp4",
        2: "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/test/H1.mp4",
        3: "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/test/lan1.mp4",
        4: "/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/test/Quay Lần 1.MOV",
    }

    ctx = mp.get_context("spawn")
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
    for p in processes:
        p.join()


if __name__ == "__main__":
    main()
