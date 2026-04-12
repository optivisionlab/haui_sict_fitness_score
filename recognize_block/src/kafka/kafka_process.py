import time
from typing import Optional, Iterable, Tuple, Dict
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import cv2
from loguru import logger
import io
import requests
from src.kafka.kafka_produce import KafkaFrameProducer
from confluent_kafka import KafkaException, KafkaError
from src.config.config import KAFKA_SERVERS


def video_worker(video_path: str, camera_id: int, producer: KafkaFrameProducer, respect_fps: bool = True):
        cap = cv2.VideoCapture(video_path)
        frame_index = 0
        if not cap.isOpened():
            logger.info(f"[camera-{camera_id}] Cannot open video {video_path}")
            return

        # lấy fps file (nếu không đọc được mặc định 25)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0 or fps != fps:  # check NaN
            fps = 25.0
        frame_interval = 1.0 / fps

        logger.info(f"[camera-{camera_id}] opened {video_path} (fps={fps:.2f})")

        try:
            while True:
                start_loop = time.time()
                ret, frame = cap.read()
                if not ret:
                    break

                sent = producer.send_frame(camera_id, frame, headers=[('frame_index', str(frame_index).encode())])
                frame_index += 1
                if not sent:
                    pass

                if respect_fps:
                    elapsed = time.time() - start_loop
                    sleep_for = frame_interval - elapsed
                    if sleep_for > 0:
                        time.sleep(sleep_for)
                else:
                    pass
        finally:
            cap.release()
            logger.info(f"[camera-{camera_id}] finished")


def create_topic(topics_name :list, 
                 number_of_partitions :int = 3, 
                 replication_factor :int = 1,
                 host_servers:str = KAFKA_SERVERS):
    

    admin = AdminClient({"bootstrap.servers": host_servers})
    topics_list = []
    
    for name in topics_name:
        topics_list.append(NewTopic(name, num_partitions=number_of_partitions, replication_factor=replication_factor))
    
    fs = admin.create_topics(topics_list)

    for t, f in fs.items():
        try:
            f.result()
            logger.info(f"✅ Created topic {t}")
        except Exception as e:
            logger.error(f"❌ Failed to create topic {t}: {e}")