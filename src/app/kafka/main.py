import threading
from src.app.kafka.kafka_produce import KafkaFrameProducer
from src.app.kafka.kafka_consumers import KafkaFrameConsumer
from src.app.kafka.untils import *


producer_conf = {
'bootstrap.servers': 'localhost:9094',
'compression.type': 'lz4',
'linger.ms': 10,
'batch.num.messages': 10000,
'message.max.bytes': 10000000,
}

consumer_conf = {"bootstrap.servers": "localhost:9094"}


# đường dẫn 4 video mẫu
VIDEO_PATHS = [
    "tmp/IMG_0034.MOV",
    "tmp/IMG_0034.MOV",
    "tmp/IMG_0034.MOV",
    "tmp/IMG_0034.MOV",
]
topics = [f"camera-{i}" for i in range(4)]
consumers = []
threads = []

create_topic(topics, number_of_partitions=4)

producer = KafkaFrameProducer(producer_conf, topic_template="camera-{camera_id}", jpeg_quality=70, drop_on_full=True)

# start 4 threads
num_consumers_per_topic = 2  

prod_threads = []
for i, p in enumerate(VIDEO_PATHS):
    t = threading.Thread(target=video_worker, args=(p, i, producer), daemon=True)
    t.start()
    prod_threads.append(t)

consumers = []
cons_threads = []

num_consumers_per_topic = 1

for topic in topics:
    group_id = f"group-{topic}"  
    for j in range(num_consumers_per_topic):
        c = KafkaFrameConsumer(consumer_conf, topic, group_id)
        th = threading.Thread(target=c.start, args=(handle_frame,), daemon=True)
        th.start()
        consumers.append(c)
        cons_threads.append(th)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Stopping...")
    for c in consumers:
        c.stop()
    for t in prod_threads:
        t.join()
    for t in cons_threads:
        t.join()
    producer.close()