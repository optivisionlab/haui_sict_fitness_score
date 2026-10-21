"""
Harness cho test tích hợp pipeline chấm điểm: chạy app (uvicorn) + fake AI ở process riêng,
dùng Kafka/Mongo/MinIO thật với DB và topic riêng cho từng lần chạy.
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId

# Nạp .env vào os.environ trước khi Pipeline sao chép biến môi trường cho subprocess
from app.core.config import settings  # noqa: F401

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
TEST_DB = os.getenv("MONGODB_DB", "fitness_score_test")


def http_json(url: str, timeout: float = 5.0, headers: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


class FakeAIProcess:
    def __init__(self, port: int = 18888, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v1/process"

    def start(self) -> "FakeAIProcess":
        self.proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS_DIR / "fake_ai_server.py"), str(self.port), self.host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                self.stats()
                return self
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        raise TimeoutError("Fake AI không khởi động")

    def stats(self) -> dict:
        return http_json(f"http://127.0.0.1:{self.port}/stats")[1]

    def stop(self) -> None:
        if self.proc:
            self.proc.kill()
            self.proc.wait()


class Pipeline:
    """Một lần chạy test: topic/group riêng, app chạy được nhiều lần (restart) trên cùng topic."""

    def __init__(self, fake_ai: FakeAIProcess, port: int = 8021, **env_overrides: str):
        run = uuid.uuid4().hex[:8]
        self.run_id = run
        self.port = port
        self.fake_ai = fake_ai
        self.env = dict(os.environ)
        self.env.update(
            {
                "MONGODB_DB": TEST_DB,
                "KAFKA_TOPIC_GRADING_JOBS": f"test-jobs-{run}",
                "KAFKA_TOPIC_GRADING_JOBS_SMALL": f"test-jobs-small-{run}",
                "KAFKA_TOPIC_GRADING_JOBS_LARGE": f"test-jobs-large-{run}",
                "KAFKA_TOPIC_GRADING_RESULTS": f"test-results-{run}",
                "KAFKA_CONSUMER_GROUP_BACKEND": f"test-backend-{run}",
                "KAFKA_CONSUMER_GROUP_AI": f"test-ai-{run}",
                "AI_MOCK_MODE": "false",
                "AI_PICKLEBALL_VIDEO_URL": fake_ai.url,
                "AI_DIRECT_FALLBACK": "false",
                "AI_WORKER_SHUTDOWN_GRACE": "5",
                # Test dùng bucket thật nhưng DB test: không được chạy job xóa object
                "UPLOAD_CLEANUP_ENABLED": "false",
            }
        )
        self.env.update(env_overrides)
        self.proc: subprocess.Popen | None = None
        self.log_path = Path(os.getenv("TEST_LOG_DIR", "/tmp")) / f"pipeline-{run}.log"
        self._log = None
        self.result_ids: list[ObjectId] = []
        self.user_ids: list[str] = []
        from pymongo import MongoClient
        from app.core.config import settings

        self._mongo = MongoClient(
            settings.MONGODB_URI, username=settings.MONGODB_USERNAME, password=settings.MONGODB_PASSWORD
        )
        self.db = self._mongo[TEST_DB]

    # ---- Kafka ----
    def create_topics(self, partitions: int = 3) -> None:
        import asyncio
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic

        names = [
            self.env["KAFKA_TOPIC_GRADING_JOBS"],
            self.env["KAFKA_TOPIC_GRADING_JOBS_SMALL"],
            self.env["KAFKA_TOPIC_GRADING_JOBS_LARGE"],
            self.env["KAFKA_TOPIC_GRADING_RESULTS"],
        ]

        async def _create():
            admin = AIOKafkaAdminClient(bootstrap_servers=self.env["KAFKA_BOOTSTRAP_SERVERS"])
            await admin.start()
            try:
                await admin.create_topics(
                    [NewTopic(name=n, num_partitions=partitions, replication_factor=1) for n in names]
                )
            finally:
                await admin.close()

        asyncio.run(_create())

    def delete_topics(self) -> None:
        import asyncio
        from aiokafka.admin import AIOKafkaAdminClient

        names = [v for k, v in self.env.items() if k.startswith("KAFKA_TOPIC_GRADING_") and v.startswith("test-")]

        async def _delete():
            admin = AIOKafkaAdminClient(bootstrap_servers=self.env["KAFKA_BOOTSTRAP_SERVERS"])
            await admin.start()
            try:
                await admin.delete_topics(names)
            finally:
                await admin.close()

        try:
            asyncio.run(asyncio.wait_for(_delete(), timeout=20))
        except Exception:
            pass  # Kafka không truy cập được (test chế độ degraded) hoặc topic chưa tạo

    def publish_raw_job(self, job: dict, topic: str | None = None) -> None:
        import asyncio
        from aiokafka import AIOKafkaProducer

        async def _send():
            producer = AIOKafkaProducer(bootstrap_servers=self.env["KAFKA_BOOTSTRAP_SERVERS"])
            await producer.start()
            try:
                await producer.send_and_wait(
                    topic or self.env["KAFKA_TOPIC_GRADING_JOBS"],
                    json.dumps(job).encode(),
                    key=str(job["resultId"]).encode(),
                )
            finally:
                await producer.stop()

        asyncio.run(_send())

    # ---- App ----
    def start_app(self, wait_ready: bool = True) -> None:
        self._log = open(self.log_path, "a")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(self.port)],
            cwd=BACKEND_DIR,
            env=self.env,
            stdout=self._log,
            stderr=subprocess.STDOUT,
        )
        if wait_ready:
            self.wait_ready()

    def wait_ready(self, timeout: float = 60) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError(f"App thoát sớm, xem log {self.log_path}")
            try:
                status, body = self.ready()
                if status == 200 and all(p.get("partitions") for p in body.get("worker_pools", {}).values()):
                    return body
            except (urllib.error.URLError, ConnectionError):
                pass
            time.sleep(0.5)
        raise TimeoutError(f"App không ready, xem log {self.log_path}")

    def ready(self) -> tuple[int, dict]:
        return http_json(f"http://127.0.0.1:{self.port}/health/ready")

    def sigterm(self, timeout: float = 90) -> None:
        self.proc.send_signal(signal.SIGTERM)
        self.proc.wait(timeout=timeout)
        self._log.close()

    def kill9(self) -> None:
        self.proc.kill()
        self.proc.wait()
        self._log.close()

    def log(self) -> str:
        return self.log_path.read_text()

    # ---- Dữ liệu ----
    def insert_job(
        self, title: str = "ok", duration_sec: int | None = None, object_key: str | None = None
    ) -> ObjectId:
        result_id = ObjectId()
        now = datetime.now(timezone.utc)
        task_id, course_id, sport_id, user_id = (str(ObjectId()) for _ in range(4))
        object_key = object_key or f"submissions/{task_id}/{result_id}.mp4"
        job = {
            "jobId": str(result_id),
            "resultId": str(result_id),
            "taskId": task_id,
            "courseId": course_id,
            "sportId": sport_id,
            "sportCode": "PICKLEBALL",
            "mode": "VIDEO",
            "userId": user_id,
            "bucket": "videos",
            "objectKey": object_key,
            "videoUrl": f"videos/{object_key}",
            "minioBucket": "videos",
            "attemptNo": 1,
            "durationSec": duration_sec,
            "detail": {"title": title, "category": "practice", "gradingMethod": "highest", "timeLimit": None},
            "schemaVersion": 1,
        }
        self.db.video_results.insert_one(
            {
                "_id": result_id,
                "taskId": task_id,
                "courseId": course_id,
                "sportId": sport_id,
                "userId": user_id,
                "attemptNo": 1,
                "pending": True,
                "status": "pending",
                "videoUrl": f"videos/{object_key}",
                "objectKey": object_key,
                "bucket": "videos",
                "durationSec": duration_sec,
                "submittedAt": now,
                "testRun": self.run_id,
                "gradingJob": job,
                "gradingJobStatus": "pending",
                "gradingJobAttempts": 0,
                "gradingJobNextAttemptAt": now,
            }
        )
        self.result_ids.append(result_id)
        self.user_ids.append(user_id)
        return result_id

    def statuses(self, ids: list[ObjectId]) -> dict[str, dict]:
        docs = self.db.video_results.find({"_id": {"$in": ids}}, {"status": 1, "error": 1, "updatedAt": 1})
        return {str(d["_id"]): d for d in docs}

    def wait_status(self, ids: list[ObjectId], statuses=("completed", "failed"), timeout: float = 300) -> dict[str, dict]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            docs = self.statuses(ids)
            if len(docs) == len(ids) and all(d.get("status") in statuses for d in docs.values()):
                return docs
            time.sleep(0.5)
        raise TimeoutError(f"Hết thời gian chờ trạng thái: {self.statuses(ids)}")

    def wait_in_flight(self, ids: list[ObjectId], timeout: float = 60) -> None:
        wanted = {str(i) for i in ids}
        deadline = time.time() + timeout
        while time.time() < deadline:
            if wanted <= set(self.fake_ai.stats()["in_flight"]):
                return
            time.sleep(0.2)
        raise TimeoutError(f"Job chưa tới AI: {wanted - set(self.fake_ai.stats()['in_flight'])}")

    def cleanup(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        self.db.video_results.delete_many({"testRun": self.run_id})
        self.db.notifications.delete_many({"userId": {"$in": self.user_ids}})
        self.delete_topics()
        self._mongo.close()

