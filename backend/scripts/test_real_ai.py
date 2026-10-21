"""
Test end-to-end với AI service thật (1 video ngắn), đi qua đúng các API công khai:
upload-url -> PUT MinIO -> confirm-upload -> outbox -> Kafka -> worker pool -> AI thật
-> result consumer -> GET /status.

    MONGODB_DB=fitness_score_test AI_REAL_URL=http://100.95.228.82:8888/api/v1/process \\
        python scripts/test_real_ai.py [đường_dẫn_video.mp4]
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bson import ObjectId

from app.services.auth_service import create_access_token
from pipeline_harness import FakeAIProcess, Pipeline

DEFAULT_VIDEO = Path("/home/aic/Cuong/fitness/pickleball_track/score_video_block/tests/fixtures/clip_5s.mp4")
AI_REAL_URL = os.getenv("AI_REAL_URL", "http://100.95.228.82:8888/api/v1/process")


def api(pipe: Pipeline, method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{pipe.port}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    assert payload["success"], payload
    return payload["data"]


def run(video: Path):
    print(f"\n[REAL AI] {AI_REAL_URL}  video={video.name} ({video.stat().st_size} bytes)")
    pipe = Pipeline(
        FakeAIProcess(),
        AI_PICKLEBALL_VIDEO_URL=AI_REAL_URL,
        AI_POOL_SMALL_CONCURRENCY="1",
        AI_MAX_CONCURRENCY="1",
    )
    db = pipe.db
    now = datetime.now(timezone.utc)
    ids = {k: ObjectId() for k in ("user", "course", "task", "enrollment")}
    object_key = None
    try:
        pipe.create_topics()
        pipe.start_app()
        sport = db.sports.find_one({"code": {"$in": ["PICKLEBALL", "PICKLE"]}})
        assert sport, "Thiếu môn PICKLEBALL trong DB test"
        db.users.insert_one({"_id": ids["user"], "name": "Real AI test", "email": f"real-ai-{pipe.run_id}@example.com",
                             "role": "student", "password": "x", "userCode": f"RA{pipe.run_id}", "createdAt": now})
        db.courses.insert_one({"_id": ids["course"], "name": "Real AI", "teacherId": str(ObjectId()), "createdAt": now})
        db.tasks.insert_one({"_id": ids["task"], "courseId": str(ids["course"]), "sportId": str(sport["_id"]),
                             "title": "Real AI pickleball", "category": "practice", "gradingMethod": "highest",
                             "timeLimit": 60, "createdAt": now})
        db.enrollments.insert_one({"_id": ids["enrollment"], "userId": str(ids["user"]),
                                   "courseId": str(ids["course"]), "status": "active", "taskScores": {},
                                   "completedTaskIds": [], "createdAt": now})
        token = create_access_token({"sub": str(ids["user"])})

        size = video.stat().st_size
        upload = api(pipe, "POST", "/api/video-results/upload-url", token, {
            "taskId": str(ids["task"]), "fileName": video.name, "contentType": "video/mp4",
            "fileSize": size, "durationSec": 5,
        })
        object_key = upload["objectKey"]
        req = urllib.request.Request(upload["uploadUrl"], data=video.read_bytes(), method="PUT",
                                     headers={"Content-Type": "video/mp4"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            assert resp.status == 200
        print(f"  ✓ upload-url + PUT MinIO ({object_key})")

        result = api(pipe, "POST", "/api/video-results/confirm-upload", token, {"uploadId": upload["uploadId"]})
        result_id = result["id"]
        print(f"  ✓ confirm-upload → resultId={result_id}, status={result['status']}")

        started = time.time()
        status = None
        while time.time() - started < 900:
            status = api(pipe, "GET", f"/api/video-results/{result_id}/status", token)
            if status["status"] in ("completed", "failed"):
                break
            time.sleep(3)
        elapsed = time.time() - started
        doc = db.video_results.find_one({"_id": ObjectId(result_id)})
        print(f"  · sau {elapsed:.0f}s: status={status['status']} aiScore={doc.get('aiScore')} "
              f"error={doc.get('error')} lane={doc.get('gradingJobLane')} metrics={doc.get('metrics')}")
        assert status["status"] == "completed", f"AI thật trả {status} (xem log {pipe.log_path})"
        assert doc.get("aiScore") is not None and doc.get("aiComment")
        enrollment = db.enrollments.find_one({"_id": ids["enrollment"]})
        assert str(ids["task"]) in enrollment.get("taskScores", {}), enrollment
        graded = db.notifications.count_documents({"userId": str(ids["user"]), "type": "submission_graded"})
        assert graded == 1, graded
        print(f"  ✓ AI thật chấm xong: aiScore={doc['aiScore']}, nhận xét='{doc['aiComment']}'")
        print(f"  ✓ Điểm đã vào enrollment.taskScores, 1 notification SUBMISSION_GRADED")
        pipe.sigterm()
    finally:
        if object_key:
            from app.services.minio_service import minio_service
            minio_service.delete_file(object_key)
        for name, coll in (("user", "users"), ("course", "courses"), ("task", "tasks"), ("enrollment", "enrollments")):
            db[coll].delete_one({"_id": ids[name]})
        db.video_results.delete_many({"userId": str(ids["user"])})
        db.video_upload_sessions.delete_many({"userId": str(ids["user"])})
        db.notifications.delete_many({"userId": str(ids["user"])})
        pipe.cleanup()


def run_load(jobs: int, object_key: str):
    """Gửi nhiều job hơn sức chứa của AI: AI trả 429 + Retry-After, backend chờ rồi gửi lại."""
    print(f"\n[REAL AI LOAD] {jobs} job đồng thời → {AI_REAL_URL} (object {object_key})")
    pipe = Pipeline(
        FakeAIProcess(),
        AI_PICKLEBALL_VIDEO_URL=AI_REAL_URL,
        AI_POOL_SMALL_CONCURRENCY=str(jobs),
        AI_MAX_CONCURRENCY=str(jobs),
        AI_MAX_RETRIES="1",
    )
    try:
        pipe.create_topics()
        pipe.start_app()
        t0 = time.time()
        ids = [pipe.insert_job("load", duration_sec=45, object_key=object_key) for _ in range(jobs)]
        docs = pipe.wait_status(ids, timeout=900)
        elapsed = time.time() - t0
        statuses = [d["status"] for d in docs.values()]
        log = pipe.log()
        busy = log.count("AI busy for resultId=")
        assert statuses.count("completed") == jobs, {s: statuses.count(s) for s in set(statuses)}
        assert busy > 0, "AI không trả 429 nào: tăng số job vượt PICKLEBALL_MAX_PENDING_JOBS"
        print(f"  ✓ {jobs}/{jobs} job completed sau {elapsed:.0f}s; backend nhận {busy} lần 429 và tự chờ gửi lại "
              f"(AI_MAX_RETRIES=1 nên nếu 429 bị tính là thất bại thì job đã failed)")
        pipe.sigterm()
    finally:
        pipe.cleanup()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "load":
        run_load(int(sys.argv[2]) if len(sys.argv) > 2 else 12, os.getenv("LOAD_OBJECT_KEY", "bench/bench_45s_270p.mp4"))
    else:
        run(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VIDEO)
    print("\n>>> TEST REAL AI PASSED")
