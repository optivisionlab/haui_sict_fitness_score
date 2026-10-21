"""
Kiểm thử T4 — AIWorkerPool (1 consumer + queue + N worker).

0. Unit: OffsetTracker chỉ commit tới offset nhỏ nhất chưa xong.
K1+K7. 9 job x 20s, 3 worker: tổng ~60s; trong lúc chấm, GET /api/auth/me < 100ms.
K2. 1 job dài 120s + 6 job ngắn 10s, 2 worker: job ngắn không phải chờ job dài.
K3. kill -9 khi 3 job đang chạy: restart thì không mất job; job đã chấm xong mà bị giao lại thì skip.
K5. AI trả 500 liên tục: retry AI_MAX_RETRIES lần rồi failed (ai_http_500); 4xx thì không retry.
K8. SIGTERM khi đang có job: job ngắn chạy xong trong grace, job dài bị hủy và được giao lại sau restart.

Chạy (cần Kafka/Mongo/MinIO thật, dùng DB/topic riêng):
    MONGODB_DB=fitness_score_test python scripts/test_worker_pool.py [unit|k1|k2|k3|k8]
"""

import statistics
import sys
import time
import urllib.request
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiokafka import TopicPartition
from bson import ObjectId

from app.services.ai_worker_pool import OffsetTracker
from pipeline_harness import FakeAIProcess, Pipeline


def test_offset_tracker():
    print("\n[TEST 0] OffsetTracker")
    tp = TopicPartition("t", 0)
    tracker = OffsetTracker()
    for offset in (10, 11, 12):
        tracker.add(tp, offset)
    tracker.done(tp, 11)
    tracker.done(tp, 12)
    assert tracker.committable() == {tp: 10}, "10 chưa xong thì không được commit qua 10"
    tracker.mark_committed({tp: 10})
    assert tracker.committable() == {}, "Không commit lại offset không đổi"
    tracker.done(tp, 10)
    assert tracker.committable() == {tp: 13}
    tracker.mark_committed({tp: 13})
    tracker.forget(tp)
    assert not tracker.owns(tp) and tracker.committable() == {}
    print("  ✓ commit dừng ở offset nhỏ nhất chưa xong, forget() xóa trạng thái")


def _completed_offsets(pipe: Pipeline, ids, t0: float) -> list[float]:
    from datetime import timezone

    # pymongo trả datetime naive (UTC): phải gắn tzinfo trước khi lấy timestamp
    docs = pipe.statuses(ids)
    return sorted(d["updatedAt"].replace(tzinfo=timezone.utc).timestamp() - t0 for d in docs.values())


def test_k1_parallel_and_k7_latency(fake_ai: FakeAIProcess):
    print("\n[K1 + K7] 9 job x 20s, 3 worker; đo GET /api/auth/me trong lúc chấm")
    from datetime import datetime, timezone
    from app.services.auth_service import create_access_token

    pipe = Pipeline(fake_ai, AI_POOL_SMALL_CONCURRENCY="3", AI_MAX_CONCURRENCY="3")
    user_id = ObjectId()
    try:
        pipe.create_topics()
        pipe.db.users.insert_one(
            {
                "_id": user_id,
                "name": "Load test",
                "email": f"load-{pipe.run_id}@example.com",
                "role": "student",
                "password": "x",
                "createdAt": datetime.now(timezone.utc),
            }
        )
        token = create_access_token({"sub": str(user_id)})
        pipe.start_app()
        before = fake_ai.stats()["max_concurrent"]
        t0 = time.time()
        ids = [pipe.insert_job("sleep:20") for _ in range(9)]
        pipe.wait_in_flight(ids[:1])

        latencies = []
        req = urllib.request.Request(
            f"http://127.0.0.1:{pipe.port}/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        while len(latencies) < 30:
            started = time.perf_counter()
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
            latencies.append((time.perf_counter() - started) * 1000)
            time.sleep(0.3)

        docs = pipe.wait_status(ids, timeout=200)
        total = max(_completed_offsets(pipe, ids, t0))
        assert all(d["status"] == "completed" for d in docs.values()), docs
        stats = fake_ai.stats()
        assert stats["max_concurrent"] == 3, stats["max_concurrent"]
        assert total < 90, f"Tổng {total:.0f}s (tuần tự ~180s)"
        print(f"  ✓ K1: 9 job xong sau {total:.0f}s (tuần tự sẽ ~180s), AI nhận tối đa {stats['max_concurrent']} request đồng thời")
        p95 = statistics.quantiles(latencies, n=20)[18]
        assert max(latencies) < 100, f"/auth/me chậm: max {max(latencies):.0f}ms"
        print(f"  ✓ K7: /api/auth/me trong lúc 3 job chạy: p95 {p95:.1f}ms, max {max(latencies):.1f}ms")
        assert before <= 3
    finally:
        pipe.db.users.delete_one({"_id": user_id})
        pipe.cleanup()


def test_k2_no_head_of_line_blocking(fake_ai: FakeAIProcess):
    print("\n[K2] 1 job dài 120s + 6 job ngắn 10s, 2 worker")
    pipe = Pipeline(fake_ai, AI_POOL_SMALL_CONCURRENCY="2", AI_MAX_CONCURRENCY="2")
    try:
        pipe.create_topics()
        pipe.start_app()
        long_id = pipe.insert_job("sleep:120")
        pipe.wait_in_flight([long_id])
        t0 = time.time()
        short_ids = [pipe.insert_job("sleep:10") for _ in range(6)]
        pipe.wait_status(short_ids, timeout=150)
        finished = _completed_offsets(pipe, short_ids, t0)
        long_status = pipe.statuses([long_id])[str(long_id)]["status"]
        assert long_status == "pending", f"Job dài đã xong sớm bất thường: {long_status}"
        assert finished[-1] < 75, f"Job ngắn xong sau {finished[-1]:.0f}s"
        print(
            f"  ✓ 6 job ngắn xong sau {finished[-1]:.0f}s trong khi job dài vẫn đang chấm "
            f"(1 worker giữ job dài, 1 worker làm lần lượt 6 job ngắn ≈ 60s)"
        )
    finally:
        pipe.cleanup()


def test_k3_kill9_no_loss_no_duplicate(fake_ai: FakeAIProcess):
    print("\n[K3] kill -9 khi 3 job đang chạy")
    pipe = Pipeline(fake_ai, AI_POOL_SMALL_CONCURRENCY="3", AI_MAX_CONCURRENCY="3")
    try:
        pipe.create_topics()
        pipe.start_app()
        ids = [pipe.insert_job("sleep:15") for _ in range(3)]
        pipe.wait_in_flight(ids)
        pipe.kill9()
        print("  · đã kill -9 khi cả 3 job đang ở AI")

        pipe.start_app()
        docs = pipe.wait_status(ids, timeout=120)
        assert all(d["status"] == "completed" for d in docs.values()), docs
        calls = fake_ai.stats()["calls"]
        assert all(calls[str(i)] == 2 for i in ids), {str(i): calls.get(str(i)) for i in ids}
        print("  ✓ Sau restart cả 3 job được giao lại và chấm xong (không mất job)")

        # Job đã chấm xong bị giao lại (crash trước khi commit offset) -> không gọi AI lần hai
        done_id = ids[0]
        job = pipe.db.video_results.find_one({"_id": done_id})["gradingJob"]
        pipe.publish_raw_job(job)
        deadline = time.time() + 30
        skipped = 0
        while time.time() < deadline:
            skipped = pipe.ready()[1]["worker_pools"]["small"]["skipped_duplicate"]
            if skipped:
                break
            time.sleep(0.5)
        assert skipped == 1, f"skipped_duplicate={skipped}"
        assert fake_ai.stats()["calls"][str(done_id)] == 2, "Job đã chấm bị gọi AI thêm lần nữa"
        print("  ✓ Job đã completed bị giao lại: skipped_duplicate=1, AI không bị gọi thêm")
        pipe.sigterm()
    finally:
        pipe.cleanup()


def test_k8_sigterm_drain(fake_ai: FakeAIProcess):
    print("\n[K8] SIGTERM khi đang có job (grace 8s): job 3s chạy xong, job 40s bị giao lại")
    pipe = Pipeline(fake_ai, AI_POOL_SMALL_CONCURRENCY="2", AI_MAX_CONCURRENCY="2", AI_WORKER_SHUTDOWN_GRACE="8")
    try:
        pipe.create_topics()
        pipe.start_app()
        short_id = pipe.insert_job("sleep:3")
        long_id = pipe.insert_job("sleep:40")
        pipe.wait_in_flight([short_id, long_id])
        started = time.time()
        pipe.sigterm()
        stop_sec = time.time() - started
        log = pipe.log()
        assert "Traceback" not in log, log[-3000:]
        assert "Draining 2 running job(s)" in log, log[-3000:]
        assert "Cancelling 1 job(s) still running after grace period" in log, log[-3000:]
        assert stop_sec < 20, stop_sec
        print(f"  ✓ Dừng sau {stop_sec:.1f}s: drain job ngắn, hủy job dài sau grace, không có traceback")

        pipe.start_app()
        docs = pipe.wait_status([short_id, long_id], timeout=120)
        assert all(d["status"] == "completed" for d in docs.values()), docs
        calls = fake_ai.stats()["calls"]
        assert calls[str(short_id)] == 1, calls[str(short_id)]
        assert calls[str(long_id)] == 2, calls[str(long_id)]
        print("  ✓ Sau restart: job ngắn không bị chấm lại (1 lần gọi AI), job dài được giao lại (2 lần)")
        pipe.sigterm()
    finally:
        pipe.cleanup()


def test_k5_ai_500(fake_ai: FakeAIProcess):
    print("\n[K5] AI trả 500 liên tục")
    pipe = Pipeline(fake_ai, AI_MAX_RETRIES="3")
    try:
        pipe.create_topics()
        pipe.start_app()
        rid = pipe.insert_job("status:500")
        docs = pipe.wait_status([rid], timeout=60)
        doc = docs[str(rid)]
        assert doc["status"] == "failed" and doc.get("error") == "ai_http_500", doc
        calls = fake_ai.stats()["calls"][str(rid)]
        assert calls == 3, calls
        print(f"  ✓ Gọi AI {calls} lần (retry lỗi tạm thời) rồi status=failed, error=ai_http_500")
        rid_422 = pipe.insert_job("status:422")
        doc = pipe.wait_status([rid_422], timeout=30)[str(rid_422)]
        assert doc.get("error") == "ai_http_422" and fake_ai.stats()["calls"][str(rid_422)] == 1, doc
        print("  ✓ AI trả 422 (lỗi vĩnh viễn): không retry, failed ngay với error=ai_http_422")
        pipe.sigterm()
    finally:
        pipe.cleanup()


def test_k5b_ai_busy(fake_ai: FakeAIProcess):
    print("\n[K5b] AI bận: 429 + Retry-After 3 lần, AI_MAX_RETRIES=1")
    pipe = Pipeline(fake_ai, AI_MAX_RETRIES="1")
    try:
        pipe.create_topics()
        pipe.start_app()
        rid = pipe.insert_job("busy:3")
        doc = pipe.wait_status([rid], timeout=60)[str(rid)]
        assert doc["status"] == "completed" and doc.get("error") is None, doc
        calls = fake_ai.stats()["calls"][str(rid)]
        assert calls == 4, calls
        print(f"  ✓ Chờ theo Retry-After rồi gửi lại ({calls} lần gọi), không tính vào AI_MAX_RETRIES=1 → completed")
        pipe.sigterm()
    finally:
        pipe.cleanup()


if __name__ == "__main__":
    selected = set(sys.argv[1:]) or {"unit", "k1", "k2", "k3", "k5", "k8"}
    if "unit" in selected:
        test_offset_tracker()
    fake_ai = FakeAIProcess().start()
    try:
        if "k1" in selected:
            test_k1_parallel_and_k7_latency(fake_ai)
        if "k2" in selected:
            test_k2_no_head_of_line_blocking(fake_ai)
        if "k3" in selected:
            test_k3_kill9_no_loss_no_duplicate(fake_ai)
        if "k5" in selected:
            test_k5_ai_500(fake_ai)
            test_k5b_ai_busy(fake_ai)
        if "k8" in selected:
            test_k8_sigterm_drain(fake_ai)
    finally:
        fake_ai.stop()
    print("\n>>> TEST WORKER POOL PASSED")
