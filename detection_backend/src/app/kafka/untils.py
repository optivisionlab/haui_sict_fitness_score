import time
from typing import Optional, Iterable, Tuple, Dict
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import cv2
from loguru import logger
import io
import requests
from src.app.kafka.kafka_produce import KafkaFrameProducer


def video_worker(video_path: str, camera_id: int, producer: KafkaFrameProducer, respect_fps: bool = True):
        cap = cv2.VideoCapture(video_path)
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

                sent = producer.send_frame(camera_id, frame)
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
                 host_servers:str = "localhost:9094"):
    

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

def call_face_search_api(image_bytes: bytes):
    url = "http://localhost:8000/faces/search"

    # convert bytes -> file-like object
    files = {
        "images": ("frame.jpg", io.BytesIO(image_bytes), "image/jpeg")
    }
    data = {
        "image_urls": "https://example.com/",
        "collection_name": "face_1",
        "tracking_frame": '{"id":[0,1],"bbox":[[0,0,600,600],[600,600,1200,1200]]}',
        "similarity_threshold": "0.9"
    }

    headers = {"accept": "application/json"}

    response = requests.post(url, headers=headers, files=files, data=data)
    return response.json()


def handle_frame(msg):
    logger.info(
        f"Consumed from {msg.topic()}[{msg.partition()}] "
        f"offset={msg.offset()} key={msg.key()} len={len(msg.value())}"
    )
    # TODO: gọi hàm call API ở đây
    '''
    Lấy ảnh ra dạng Byte bằng lệnh msg.value() 
    '''
    image_bytes = msg.value()
    logger.info(
        f"Consumed from {msg.topic()}[{msg.partition()}] "
        f"offset={msg.offset()} size={len(image_bytes)}"
    )
    result = call_face_search_api(image_bytes)
    logger.info(f"API response: {result}")