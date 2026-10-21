"""
Kiểm thử T5 — 2 làn theo thời lượng và timeout động.

1. Unit: chọn làn theo ngưỡng, timeout = min(BASE + PER_SEC x duration, MAX).
2. 5 video dài (làn large, concurrency 1) vào cùng lúc -> video ngắn (làn small) vẫn được chấm ngay.
3. Job còn trên topic cũ video-grading-jobs vẫn được consume (chuyển đổi topic).

    MONGODB_DB=fitness_score_test python scripts/test_lanes.py
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

from app.core.config import settings
from app.services.grading_lanes import compute_ai_timeout, lane_topic, resolve_lane
from pipeline_harness import FakeAIProcess, Pipeline


def test_unit():
    print("\n[TEST 1] Chọn làn và timeout động")
    assert resolve_lane(None) == "small"
    assert resolve_lane(90) == "small"
    assert resolve_lane(91) == "large"
    assert lane_topic("large") == settings.KAFKA_TOPIC_GRADING_JOBS_LARGE
    assert compute_ai_timeout({}) == settings.AI_API_TIMEOUT_SECONDS
    assert compute_ai_timeout({"durationSec": 30}) == 60 + 4 * 30
    assert compute_ai_timeout({"durationSec": "45"}) == 60 + 4 * 45
    assert compute_ai_timeout({"durationSec": 1000}) == 1800
    assert compute_ai_timeout({"durationSec": "abc"}) == settings.AI_API_TIMEOUT_SECONDS
    print("  ✓ ≤90s/thiếu → small, >90s → large; timeout 30s→180s, 1000s→1800s (trần), thiếu → 600s")


def test_long_videos_do_not_block_short(fake_ai: FakeAIProcess):
    print("\n[TEST 2] 5 video dài vào cùng lúc, sau đó 2 video ngắn")
    pipe = Pipeline(fake_ai, AI_POOL_SMALL_CONCURRENCY="2", AI_POOL_LARGE_CONCURRENCY="1", AI_MAX_CONCURRENCY="3")
    try:
        pipe.create_topics()
        pipe.start_app()
        long_ids = [pipe.insert_job("sleep:60", duration_sec=300) for _ in range(5)]
        pipe.wait_in_flight(long_ids[:1])
        t0 = time.time()
        short_ids = [pipe.insert_job("sleep:2", duration_sec=30) for _ in range(2)]
        pipe.wait_status(short_ids, timeout=60)
        elapsed = time.time() - t0
        longs = pipe.statuses(long_ids)
        assert elapsed < 15, f"Video ngắn chờ {elapsed:.0f}s"
        assert sum(d["status"] == "pending" for d in longs.values()) == 5, longs
        lanes = {
            str(d["_id"]): d.get("gradingJobLane")
            for d in pipe.db.video_results.find({"_id": {"$in": long_ids + short_ids}}, {"gradingJobLane": 1})
        }
        assert all(lanes[str(i)] == "large" for i in long_ids), lanes
        assert all(lanes[str(i)] == "small" for i in short_ids), lanes
        stats = fake_ai.stats()
        long_in_flight = len(set(stats["in_flight"]) & {str(i) for i in long_ids})
        assert long_in_flight == 1, f"Làn large chạy {long_in_flight} job cùng lúc (cấu hình 1)"
        print(f"  ✓ 2 video ngắn xong sau {elapsed:.1f}s; 5 video dài vẫn pending, làn large chỉ chạy 1 job/lần")

        pipe.sigterm()
        log = pipe.log()
        assert "[small] Graded" in log and "timeout=180.0" in log, "Thiếu log timeout làn small"
        print("  ✓ Log ghi lane + timeout động (video 30s → timeout=180.0)")
    finally:
        pipe.cleanup()


def test_legacy_topic_still_consumed(fake_ai: FakeAIProcess):
    print("\n[TEST 3] Job tồn đọng trên topic cũ")
    pipe = Pipeline(fake_ai, AI_WORKER_ENABLED="true")
    try:
        pipe.create_topics()
        rid = pipe.insert_job("ok")
        job = pipe.db.video_results.find_one({"_id": rid})["gradingJob"]
        # Giả lập job đã được bản cũ publish vào topic cũ: outbox không gửi lại nữa
        pipe.db.video_results.update_one({"_id": rid}, {"$set": {"gradingJobStatus": "sent"}})
        pipe.publish_raw_job(job, topic=pipe.env["KAFKA_TOPIC_GRADING_JOBS"])
        pipe.start_app()
        pipe.wait_status([rid], timeout=60)
        assert pipe.statuses([rid])[str(rid)]["status"] == "completed"
        print("  ✓ Job trên topic cũ được pool small consume và chấm xong")
        pipe.sigterm()
    finally:
        pipe.cleanup()


if __name__ == "__main__":
    test_unit()
    fake_ai = FakeAIProcess().start()
    try:
        test_long_videos_do_not_block_short(fake_ai)
        test_legacy_topic_still_consumed(fake_ai)
    finally:
        fake_ai.stop()
    print("\n>>> TEST LANES PASSED")
