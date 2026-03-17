from confluent_kafka import Consumer, KafkaException
from loguru import logger


class KafkaFrameConsumer:
    def __init__(self, consumer_conf, topic, group_id):
        self.topic = topic
        self.group_id = group_id
        self.consumer = Consumer({
            **consumer_conf,
            "group.id": group_id,
            "auto.offset.reset": "latest",
        })
        self.running = False

    def start(self, handle_message):
        self.consumer.subscribe([self.topic])
        self.running = True
        logger.info(f"[{self.group_id}] Subscribed to {self.topic}")
        try:
            while self.running:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    raise KafkaException(msg.error())
                handle_message(msg)
                self.consumer.commit(message=msg, asynchronous=True)
        finally:
            self.consumer.close()

    def stop(self):
        self.running = False