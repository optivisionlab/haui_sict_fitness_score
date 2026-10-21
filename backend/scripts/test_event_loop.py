"""
Kiểm thử T7: I/O đồng bộ (pymongo, MinIO SDK) không được chặn event loop.

Giả lập Mongo/MinIO chậm (mỗi lời gọi chặn thread 0.3s) rồi đo độ trễ event loop
trong lúc chạy outbox, result consumer, AI client và dependency xác thực.
Nếu còn chỗ gọi đồng bộ trực tiếp trên loop, độ trễ sẽ >= 300ms.
"""

import asyncio
import importlib
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId

BLOCK_SEC = 0.3
MAX_LAG_SEC = 0.1


def slow(return_value=None):
    def _fn(*args, **kwargs):
        time.sleep(BLOCK_SEC)
        return return_value

    return _fn


class LagMonitor:
    def __init__(self, interval: float = 0.01):
        self.interval = interval
        self.max_lag = 0.0
        self._task: asyncio.Task | None = None

    async def _run(self):
        while True:
            started = time.monotonic()
            await asyncio.sleep(self.interval)
            self.max_lag = max(self.max_lag, time.monotonic() - started - self.interval)

    async def __aenter__(self):
        self._task = asyncio.create_task(self._run())
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *exc):
        # Cho monitor 1 nhịp để ghi nhận lần loop bị chặn gần nhất rồi mới dừng
        await asyncio.sleep(self.interval * 3)
        self._task.cancel()


def check(name: str, monitor: LagMonitor):
    assert monitor.max_lag < MAX_LAG_SEC, f"{name}: event loop bị chặn {monitor.max_lag * 1000:.0f}ms"
    print(f"  ✓ {name}: độ trễ loop tối đa {monitor.max_lag * 1000:.0f}ms")


async def test_outbox():
    grading_outbox = importlib.import_module("app.services.grading_outbox")

    doc = {"_id": ObjectId(), "gradingJob": {"resultId": "r1"}, "gradingJobAttempts": 0}
    collection = MagicMock()
    calls = {"n": 0}

    def find_one_and_update(*args, **kwargs):
        calls["n"] += 1
        return slow(doc if calls["n"] == 1 else None)()

    collection.find_one_and_update = find_one_and_update
    collection.update_one = slow()
    fake_db = SimpleNamespace(video_results=collection)

    producer = MagicMock()
    producer.is_ready = True

    async def publish(job):
        return True

    producer.publish_grading_job = publish
    with patch.object(grading_outbox, "get_db", return_value=fake_db), \
         patch.object(grading_outbox, "kafka_producer", producer):
        async with LagMonitor() as monitor:
            dispatched = await grading_outbox.grading_outbox_dispatcher.dispatch_pending()
    assert dispatched == 1
    check("outbox (Kafka) — 3 lời gọi Mongo chậm", monitor)

    calls["n"] = 0
    producer.is_ready = False
    fake_result = {"aiScore": 8.0, "aiComment": "ok", "metrics": {}}

    async def fake_grade(job, timeout=None):
        return fake_result

    client_module = importlib.import_module("app.services.ai_grading_client")
    vrs_module = importlib.import_module("app.services.video_result_service")

    with patch.object(grading_outbox, "get_db", return_value=fake_db), \
         patch.object(grading_outbox, "kafka_producer", producer), \
         patch.object(client_module.ai_grading_client, "grade", fake_grade), \
         patch.object(vrs_module.video_result_service, "ai_callback", slow()):
        async with LagMonitor() as monitor:
            dispatched = await grading_outbox.grading_outbox_dispatcher.dispatch_pending()
    assert dispatched == 1
    check("outbox (direct fallback) — ai_callback + Mongo chậm", monitor)


async def test_result_consumer():
    consumer_module = importlib.import_module("app.services.kafka_consumer")
    vrs_module = importlib.import_module("app.services.video_result_service")

    messages = [
        SimpleNamespace(value={"resultId": "r1", "status": "completed", "aiScore": 8, "metrics": {}}),
        SimpleNamespace(value={"resultId": "r2", "status": "failed", "errorCode": "ai_http_500"}),
    ]
    service = consumer_module.KafkaResultConsumerService()

    class FakeConsumer:
        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            for m in messages:
                yield m
            service._is_running = False

    service._consumer = FakeConsumer()
    service._is_running = True
    with patch.object(vrs_module.video_result_service, "ai_callback", slow()), \
         patch.object(vrs_module.video_result_service, "ai_failure", slow()):
        async with LagMonitor() as monitor:
            await service._consume_loop()
    check("result consumer — ai_callback/ai_failure chậm", monitor)


async def test_ai_client_build_request():
    from app.services.ai_grading_client import AIGradingClient

    client = AIGradingClient(mock_mode=True)
    with patch("app.services.minio_service.minio_service.get_presigned_url", slow("http://x")):
        job = {
            "jobId": "j", "resultId": "r", "taskId": "t", "courseId": "c", "sportId": "s",
            "userId": "u", "objectKey": "submissions/t/r.mp4", "sportCode": "PICKLEBALL", "mode": "VIDEO",
        }
        async with LagMonitor() as monitor:
            result = await client.grade(job)
    assert result["status"] == "completed"
    check("AI client — ký presigned URL chậm", monitor)


async def test_auth_dependencies():
    from app.models.user import User, UserRole
    auth_service = importlib.import_module("app.services.auth_service")

    user = User(id=str(ObjectId()), name="T", email="t@example.com", role=UserRole.TEACHER, password="x")
    token = auth_service.create_access_token({"sub": user.id})
    creds = SimpleNamespace(credentials=token)
    with patch.object(auth_service.crud_user, "get", slow(user)):
        async with LagMonitor() as monitor:
            current = await auth_service.get_current_user(creds)
            assert current.id == user.id
            assert await auth_service.verify_internal_api_key(api_key=None, credentials=creds)
    check("get_current_user + verify_internal_api_key", monitor)

    course = SimpleNamespace(teacher_id=user.id)
    enrollment = SimpleNamespace(status=SimpleNamespace(value="active"))
    with patch("app.crud.course.crud_course.get", slow(course)), \
         patch("app.crud.enrollment.crud_enrollment.get_by_user_and_course", slow(enrollment)):
        async with LagMonitor() as monitor:
            assert await auth_service.verify_course_teacher("c1", current_user=user) is course
            assert await auth_service.verify_student_in_course("c1", current_user=user) is enrollment
    check("verify_course_teacher + verify_student_in_course", monitor)


async def run():
    print("\n[TEST T7] Event loop không bị chặn bởi I/O đồng bộ")
    await test_outbox()
    await test_result_consumer()
    await test_ai_client_build_request()
    await test_auth_dependencies()


if __name__ == "__main__":
    asyncio.run(run())
    print("\n>>> TEST EVENT LOOP PASSED")
