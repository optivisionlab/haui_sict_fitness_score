import time
from typing import Optional, Iterable, Tuple, Dict
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import cv2
from loguru import logger


class KafkaFrameProducer:
    """
    Producer helper gửi frames (numpy array) tới Kafka topics.
    - topic_template: e.g. "camera-{camera_id}" -> topic cho mỗi camera
    - producer_conf: dict cấu hình cho confluent_kafka. Thêm bootstrap.servers, compression.type,...
    - jpeg_quality: 0-100
    - drop_on_full: nếu True thì drop frame khi local queue đầy, ngược lại sẽ chờ một khoảng ngắn để retry
    - max_backoff_sec: tổng thời gian chờ khi queue đầy (nếu drop_on_full=False)
    """
    def __init__(
        self,
        producer_conf: Dict,
        topic_template: str = "camera-{camera_id}",
        jpeg_quality: int = 70,
        drop_on_full: bool = True,
        max_backoff_sec: float = 0.2,
    ):
        if 'bootstrap.servers' not in producer_conf:
            raise ValueError("producer_conf phải chứa 'bootstrap.servers'")
        self.producer = Producer(producer_conf)
        self.topic_template = topic_template
        self.jpeg_quality = int(jpeg_quality)
        self.drop_on_full = bool(drop_on_full)
        self.max_backoff_sec = float(max_backoff_sec)

    def _encode_frame_to_jpeg(self, frame) -> Optional[bytes]:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, self.jpeg_quality))]
        ok, buf = cv2.imencode('.jpg', frame, encode_param)
        if not ok:
            return None
        return buf.tobytes()

    def _topic_for(self, camera_id) -> str:
        return self.topic_template.format(camera_id=camera_id)

    def _default_headers(self, camera_id) -> Iterable[Tuple[str, bytes]]:
        ts = int(time.time() * 1000)
        return [('camera_id', str(camera_id).encode()), ('ts', str(ts).encode())]

    def send_frame(
        self,
        camera_id,
        frame,
        key: Optional[bytes] = None,
        headers: Optional[Iterable[Tuple[str, bytes]]] = None,
    ) -> bool:
        """
        Encode và gửi frame tới topic camera-{camera_id}.
        Trả về True nếu message được quăng vào producer queue thành công.
        Nếu queue đầy và drop_on_full=True -> trả về False.
        Nếu queue đầy và drop_on_full=False -> sẽ retry trong giới hạn max_backoff_sec.
        """
        payload = self._encode_frame_to_jpeg(frame)
        if payload is None:
            return False

        topic = self._topic_for(camera_id)
        hdrs = list(headers) if headers else []
        hdrs.extend(self._default_headers(camera_id))

        start = time.time()
        while True:
            try:
                self.producer.produce(topic=topic, key=key, value=payload, headers=hdrs, callback=self._delivery_report)
                self.producer.poll(0)
                return True
            except BufferError:
                if self.drop_on_full:
                    return False
                else:
                    elapsed = time.time() - start
                    if elapsed >= self.max_backoff_sec:
                        return False
                    time.sleep(0.01)

    def send_bytes(
        self,
        camera_id,
        payload: bytes,
        key: Optional[bytes] = None,
        headers: Optional[Iterable[Tuple[str, bytes]]] = None,
    ) -> bool:
        """Gửi payload bytes trực tiếp (nếu bạn đã encode từ trước)."""
        topic = self._topic_for(camera_id)
        hdrs = list(headers) if headers else []
        hdrs.extend(self._default_headers(camera_id))

        try:
            self.producer.produce(topic=topic, key=key, value=payload, headers=hdrs, callback=self._delivery_report)
            self.producer.poll(0)
            return True
        except BufferError:
            if self.drop_on_full:
                return False
            else:
                time.sleep(0.01)
                try:
                    self.producer.produce(topic=topic, key=key, value=payload, headers=hdrs, callback=self._delivery_report)
                    self.producer.poll(0)
                    return True
                except BufferError:
                    return False

    def _delivery_report(self, err, msg):
        """Callback khi message đã được gửi (thành công hoặc lỗi)."""
        if err is not None:
            # production: log vào file/monitoring thay vì logger.info
            logger.info(f"Delivery failed for topic {msg.topic()}: {err}")
        else:
            # ít in để tránh I/O overhead
            pass

    def flush(self, timeout: Optional[float] = 10.0):
        """Flush tất cả message chờ đến broker (block tối đa timeout giây)."""
        self.producer.flush(timeout)

    def close(self, timeout: Optional[float] = 10.0):
        self.flush(timeout)

    # context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    pass
