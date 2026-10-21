"""
Kiểm thử T6 — Result Consumer commit thủ công và idempotent.

K6. Cùng 1 kết quả publish 3 lần -> chỉ 1 notification SUBMISSION_GRADED, điểm không đổi.
    Kết quả failed đến muộn không ghi đè completed; failed rồi completed thì thành completed.
R.  Ghi Mongo lỗi tạm thời -> message được xử lý lại (seek), offset chỉ commit sau khi ghi xong.

    MONGODB_DB=fitness_score_test python scripts/test_result_consumer.py
"""

import asyncio
import importlib
import sys
import time
from pathlib import Path
from unittest.mock import patch

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_harness import FakeAIProcess, Pipeline


def completed_result(result_id, score=8.0):
    rid = str(result_id)
    return {"jobId": rid, "resultId": rid, "status": "completed", "aiScore": score,
            "aiComment": "ok", "metrics": {"accuracy": 0.8}}


def failed_result(result_id, code="ai_http_500"):
    rid = str(result_id)
    return {"jobId": rid, "resultId": rid, "status": "failed", "errorCode": code}


def wait_until(predicate, timeout=30, interval=0.3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError("Hết thời gian chờ")


def test_k6_idempotent(pipe: Pipeline):
    print("\n[K6] Publish cùng 1 kết quả 3 lần")
    results_topic = pipe.env["KAFKA_TOPIC_GRADING_RESULTS"]
    rid = pipe.insert_job()
    user_id = pipe.db.video_results.find_one({"_id": rid})["userId"]
    for score in (8.0, 8.0, 8.0):
        pipe.publish_raw_job(completed_result(rid, score), topic=results_topic)
    wait_until(lambda: pipe.statuses([rid])[str(rid)].get("status") == "completed")
    time.sleep(5)  # chờ 2 bản trùng còn lại được xử lý
    graded = pipe.db.notifications.count_documents({"userId": user_id, "type": "submission_graded"})
    doc = pipe.db.video_results.find_one({"_id": rid})
    assert graded == 1, f"{graded} notification SUBMISSION_GRADED"
    assert doc["aiScore"] == 8.0
    print(f"  ✓ 1 notification SUBMISSION_GRADED, aiScore={doc['aiScore']}")

    pipe.publish_raw_job(completed_result(rid, 2.0), topic=results_topic)
    pipe.publish_raw_job(failed_result(rid), topic=results_topic)
    time.sleep(5)
    doc = pipe.db.video_results.find_one({"_id": rid})
    graded = pipe.db.notifications.count_documents({"userId": user_id, "type": "submission_graded"})
    assert doc["status"] == "completed" and doc.get("error") is None and doc["aiScore"] == 8.0, doc
    assert graded == 1
    print("  ✓ Kết quả khác/failed đến muộn không ghi đè completed (aiScore vẫn 8.0, không có error)")

    rid2 = pipe.insert_job()
    pipe.publish_raw_job(failed_result(rid2, "ai_unreachable"), topic=results_topic)
    wait_until(lambda: pipe.statuses([rid2])[str(rid2)].get("status") == "failed")
    pipe.publish_raw_job(completed_result(rid2, 7.0), topic=results_topic)
    wait_until(lambda: pipe.statuses([rid2])[str(rid2)].get("status") == "completed")
    doc = pipe.db.video_results.find_one({"_id": rid2})
    assert doc.get("error") is None and doc["aiScore"] == 7.0, doc
    print("  ✓ failed rồi completed -> completed, xóa error")


async def _run_consumer_with_transient_errors(pipe: Pipeline, rid) -> tuple[int, int, int]:
    from aiokafka import AIOKafkaConsumer, TopicPartition
    from app.core.config import settings

    consumer_module = importlib.import_module("app.services.kafka_consumer")
    vrs_module = importlib.import_module("app.services.video_result_service")
    real_callback = vrs_module.video_result_service.ai_callback
    calls = {"n": 0}

    def flaky_callback(result_id, ai_update):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("Mongo tạm thời không phản hồi")
        return real_callback(result_id, ai_update)

    topic = pipe.env["KAFKA_TOPIC_GRADING_RESULTS"]
    group = f"test-retry-{pipe.run_id}"
    service = consumer_module.KafkaResultConsumerService()
    with patch.object(settings, "KAFKA_TOPIC_GRADING_RESULTS", topic), \
         patch.object(settings, "KAFKA_CONSUMER_GROUP_BACKEND", group), \
         patch.object(consumer_module, "RESULT_RETRY_DELAY_SEC", 0.5), \
         patch.object(vrs_module.video_result_service, "ai_callback", flaky_callback):
        await service.start()
        try:
            deadline = time.time() + 40
            while time.time() < deadline:
                doc = await asyncio.to_thread(pipe.db.video_results.find_one, {"_id": rid})
                if doc and doc.get("status") == "completed":
                    break
                await asyncio.sleep(0.3)
            await asyncio.sleep(1)
        finally:
            await service.stop()

    checker = AIOKafkaConsumer(bootstrap_servers=pipe.env["KAFKA_BOOTSTRAP_SERVERS"], group_id=group)
    await checker.start()
    try:
        partitions = [TopicPartition(topic, p) for p in checker.partitions_for_topic(topic) or []]
        committed = 0
        for tp in partitions:
            committed += await checker.committed(tp) or 0
        end_offsets = await checker.end_offsets(partitions)
        return calls["n"], committed, sum(end_offsets.values())
    finally:
        await checker.stop()


def test_retry_on_transient_error(pipe: Pipeline):
    print("\n[R] Ghi Mongo lỗi tạm thời 2 lần")
    rid = pipe.insert_job()
    pipe.publish_raw_job(completed_result(rid, 9.0), topic=pipe.env["KAFKA_TOPIC_GRADING_RESULTS"])
    calls, committed, end = asyncio.run(_run_consumer_with_transient_errors(pipe, rid))
    doc = pipe.db.video_results.find_one({"_id": rid})
    assert doc["status"] == "completed" and doc["aiScore"] == 9.0, doc
    assert calls >= 3, calls
    assert committed == end, f"committed={committed} end={end}"
    print(f"  ✓ 2 lần ghi lỗi được seek lại và xử lý tiếp ({calls} lần gọi ai_callback cho cả topic); committed = end offset ({committed})")


if __name__ == "__main__":
    fake_ai = FakeAIProcess()
    # Không chạy AI worker: chỉ kiểm thử phía nhận kết quả
    pipe = Pipeline(fake_ai, AI_WORKER_ENABLED="false")
    try:
        pipe.create_topics()
        pipe.start_app()
        test_k6_idempotent(pipe)
        pipe.sigterm()
        test_retry_on_transient_error(pipe)
    finally:
        pipe.cleanup()
    print("\n>>> TEST RESULT CONSUMER PASSED")
