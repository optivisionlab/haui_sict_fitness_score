"""
Kiểm thử T10 — giới hạn nộp bài và dọn object bỏ dở.

1. upload-url chặn duration_sec > task.timeLimit.
2. Không giới hạn số lần nộp: task.maxAttempts không chặn upload-url.
3. Job dọn dẹp chỉ xóa object submissions/{taskId}/{resultId}.ext đủ cũ, task thuộc DB này,
   không có video_results và không có phiên upload đang mở (chạy trên bucket test riêng).

    MONGODB_DB=fitness_score_test python scripts/test_submission_limits.py
"""

import io
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db
from app.schemas.video_result import VideoUploadUrlRequest
from app.services.minio_service import minio_service
from app.services.upload_cleanup import orphan_upload_cleaner
from app.services.video_result_service import video_result_service


def expect_400(fn, contains: str):
    try:
        fn()
    except HTTPException as exc:
        assert exc.status_code == 400 and contains in exc.detail, (exc.status_code, exc.detail)
        return exc.detail
    raise AssertionError(f"Không bị chặn (chờ lỗi chứa '{contains}')")


def test_limits(db, run_id: str, ids: dict):
    print("\n[TEST 1-2] timeLimit và không giới hạn số lần nộp ở upload-url")
    now = datetime.now(timezone.utc)
    db.sports.insert_one({"_id": ids["sport"], "code": f"TEST-{run_id}", "name": "Test", "mode": "video", "createdAt": now})
    db.courses.insert_one({"_id": ids["course"], "name": "C", "teacherId": str(ObjectId()), "createdAt": now})
    db.tasks.insert_one({
        "_id": ids["task"], "courseId": str(ids["course"]), "sportId": str(ids["sport"]), "title": "T",
        "category": "practice", "gradingMethod": "highest", "timeLimit": 60, "maxAttempts": 2, "createdAt": now,
    })
    user_id = str(ids["user"])
    db.enrollments.insert_one({"_id": ids["enrollment"], "userId": user_id, "courseId": str(ids["course"]),
                               "status": "active", "createdAt": now})

    def request(duration):
        return VideoUploadUrlRequest(task_id=str(ids["task"]), file_name="a.mp4", content_type="video/mp4",
                                     file_size=1000, duration_sec=duration)

    detail = expect_400(lambda: video_result_service.create_upload_url(user_id, request(61)), "vượt thời lượng")
    print(f"  ✓ duration 61s > timeLimit 60s: {detail}")

    base = {"taskId": str(ids["task"]), "userId": user_id, "sportId": str(ids["sport"]), "submittedAt": now,
            "testRun": run_id, "pending": False}
    db.video_results.insert_many([
        {**base, "attemptNo": 1, "status": "failed", "error": "ai_unreachable"},
        {**base, "attemptNo": 2, "status": "completed", "aiScore": 8.0},
    ])
    resp = video_result_service.create_upload_url(user_id, request(60))
    session = db.video_upload_sessions.find_one({"resultId": ObjectId(resp.result_id)})
    print(f"  ✓ 1 completed + 1 failed → vẫn được nộp, attemptNo={session['attemptNo']}")
    resp_extra = video_result_service.create_upload_url(user_id, request(30))
    assert resp_extra.upload_id
    print("  ✓ Vượt maxAttempts=2 vẫn được nộp (không giới hạn số lần nộp)")
    db.video_upload_sessions.delete_many({"userId": user_id})
    resp2 = video_result_service.create_upload_url(user_id, request(None))
    assert resp2.upload_id
    print("  ✓ Không gửi duration_sec → không chặn theo timeLimit (tương thích client cũ)")


def test_cleanup(db, run_id: str, ids: dict):
    print("\n[TEST 3] Dọn object bỏ dở (bucket test riêng)")
    bucket = f"test-cleanup-{run_id}"
    minio_service.client.make_bucket(bucket)
    task = str(ids["task"])
    orphan, with_result, uploading, unknown_task = ObjectId(), ObjectId(), ObjectId(), ObjectId()
    keys = {
        "orphan": f"submissions/{task}/{orphan}.mp4",
        "with_result": f"submissions/{task}/{with_result}.mp4",
        "uploading": f"submissions/{task}/{uploading}.mov",
        "unknown_task": f"submissions/{ObjectId()}/{unknown_task}.mp4",
        "not_pattern": "submissions/readme.txt",
        "other_prefix": f"{ObjectId()}/{task}/user_attempt1_1.mp4",
    }
    try:
        for key in keys.values():
            minio_service.client.put_object(bucket, key, io.BytesIO(b"x"), 1)
        db.video_results.insert_one({"_id": with_result, "taskId": task, "userId": "u", "sportId": "s",
                                     "testRun": run_id, "status": "completed"})
        db.video_upload_sessions.insert_one({"_id": ObjectId(), "resultId": uploading, "userId": "cleanup-test",
                                             "status": "uploading",
                                             "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=10)})

        deleted = orphan_upload_cleaner.cleanup_once(bucket=bucket)
        assert deleted == [], deleted
        print("  ✓ Object mới tạo (chưa quá 24h) không bị xóa")

        deleted = orphan_upload_cleaner.cleanup_once(bucket=bucket, max_age_sec=0)
        assert deleted == [keys["orphan"]], deleted
        remaining = {o.object_name for o in minio_service.client.list_objects(bucket, recursive=True)}
        assert remaining == set(keys.values()) - {keys["orphan"]}, remaining
        print("  ✓ Chỉ xóa object bỏ dở; giữ object có bài nộp, đang upload, task lạ, sai mẫu key, khác prefix")
    finally:
        for obj in minio_service.client.list_objects(bucket, recursive=True):
            minio_service.client.remove_object(bucket, obj.object_name)
        minio_service.client.remove_bucket(bucket)
        db.video_upload_sessions.delete_many({"userId": "cleanup-test"})


if __name__ == "__main__":
    db = get_db()
    run_id = uuid.uuid4().hex[:8]
    ids = {name: ObjectId() for name in ("sport", "course", "task", "user", "enrollment")}
    try:
        test_limits(db, run_id, ids)
        test_cleanup(db, run_id, ids)
    finally:
        db.sports.delete_one({"_id": ids["sport"]})
        db.courses.delete_one({"_id": ids["course"]})
        db.tasks.delete_one({"_id": ids["task"]})
        db.enrollments.delete_one({"_id": ids["enrollment"]})
        db.video_results.delete_many({"testRun": run_id})
        db.video_upload_sessions.delete_many({"userId": str(ids["user"])})
    print("\n>>> TEST SUBMISSION LIMITS PASSED")
