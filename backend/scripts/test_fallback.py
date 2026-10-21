"""
Kiểm thử T8 (+ K4) — Direct fallback khi Kafka không sẵn sàng.

1. Kafka chết: outbox gọi AI trực tiếp, job dài không chặn job ngắn, tối đa AI_MAX_CONCURRENCY request,
   API vẫn phản hồi.
2. Tắt app khi job fallback đang chạy: chờ trong grace rồi hủy; job bị hủy được trả về pending
   (không phải chờ hết lease), restart thì chấm tiếp.

    MONGODB_DB=fitness_score_test python scripts/test_fallback.py
"""

import sys
import time
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_harness import FakeAIProcess, Pipeline, http_json

KAFKA_DOWN = "127.0.0.1:1"


def test_fallback_runs_concurrently(fake_ai: FakeAIProcess):
    print("\n[TEST 1] Kafka chết: 1 job dài 30s + 2 job ngắn 2s, AI_MAX_CONCURRENCY=2")
    pipe = Pipeline(
        fake_ai,
        KAFKA_BOOTSTRAP_SERVERS=KAFKA_DOWN,
        AI_DIRECT_FALLBACK="true",
        AI_MAX_CONCURRENCY="2",
    )
    try:
        pipe.start_app()
        status, body = pipe.ready()
        assert status == 200 and body["components"]["kafka"] == "degraded", body
        before = fake_ai.stats()["max_concurrent"]

        long_id = pipe.insert_job("sleep:30")
        pipe.wait_in_flight([long_id])
        t0 = time.time()
        short_ids = [pipe.insert_job("sleep:2") for _ in range(2)]

        worst = 0.0
        deadline = time.time() + 25
        while time.time() < deadline:
            started = time.perf_counter()
            code, _ = http_json(f"http://127.0.0.1:{pipe.port}/health/ready")
            worst = max(worst, (time.perf_counter() - started) * 1000)
            assert code == 200
            docs = pipe.statuses(short_ids)
            if all(d.get("status") == "completed" for d in docs.values()):
                break
            time.sleep(0.2)
        elapsed = time.time() - t0
        assert all(d.get("status") == "completed" for d in pipe.statuses(short_ids).values())
        assert pipe.statuses([long_id])[str(long_id)]["status"] == "pending"
        assert elapsed < 12, f"Job ngắn chờ {elapsed:.0f}s (code cũ: chờ hết job dài 30s)"
        assert worst < 100, f"API chậm {worst:.0f}ms"
        stats = fake_ai.stats()
        assert stats["max_concurrent"] <= max(2, before), stats["max_concurrent"]
        print(f"  ✓ 2 job ngắn xong sau {elapsed:.1f}s trong khi job dài còn chạy; AI tối đa {stats['max_concurrent']} request đồng thời")
        print(f"  ✓ API vẫn phản hồi trong lúc fallback chạy (chậm nhất {worst:.0f}ms)")

        pipe.wait_status([long_id], timeout=60)
        doc = pipe.db.video_results.find_one({"_id": long_id})
        assert doc["status"] == "completed" and doc["gradingJobStatus"] == "completed", doc
        print("  ✓ Job dài chấm xong, gradingJobStatus=completed")
        pipe.sigterm()
    finally:
        pipe.cleanup()


def test_fallback_shutdown_releases_job(fake_ai: FakeAIProcess):
    print("\n[TEST 2] Tắt app khi job fallback đang chạy (grace 3s)")
    pipe = Pipeline(
        fake_ai,
        KAFKA_BOOTSTRAP_SERVERS=KAFKA_DOWN,
        AI_DIRECT_FALLBACK="true",
        AI_WORKER_SHUTDOWN_GRACE="3",
    )
    try:
        pipe.start_app()
        rid = pipe.insert_job("sleep:20")
        pipe.wait_in_flight([rid])
        started = time.time()
        pipe.sigterm()
        stop_sec = time.time() - started
        log = pipe.log()
        assert "Cancelled 1 direct-fallback job(s) after grace period" in log, log[-2000:]
        assert "Traceback" not in log, log[-3000:]
        doc = pipe.db.video_results.find_one({"_id": rid})
        assert doc["gradingJobStatus"] == "pending" and "gradingJobLeaseUntil" not in doc, doc
        print(f"  ✓ Dừng sau {stop_sec:.1f}s, job bị hủy được trả về pending (không giữ lease)")

        pipe.start_app()
        pipe.wait_status([rid], timeout=60)
        assert pipe.statuses([rid])[str(rid)]["status"] == "completed"
        assert fake_ai.stats()["calls"][str(rid)] == 2
        print("  ✓ Restart thì job được chấm lại ngay và hoàn thành")
        pipe.sigterm()
    finally:
        pipe.cleanup()


if __name__ == "__main__":
    fake_ai = FakeAIProcess().start()
    try:
        test_fallback_runs_concurrently(fake_ai)
        test_fallback_shutdown_releases_job(fake_ai)
    finally:
        fake_ai.stop()
    print("\n>>> TEST FALLBACK PASSED")
