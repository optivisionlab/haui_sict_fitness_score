"""
Kiểm thử T9 — quyền xem bài nộp: GET /api/video-results/{id} và /{id}/status.
Chỉ chủ bài nộp, giáo viên của khóa học hoặc admin được xem.

    MONGODB_DB=fitness_score_test python scripts/test_result_access.py
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.services.auth_service import create_access_token


def run():
    db = get_db()
    run_id = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    users = {name: ObjectId() for name in ("owner", "other_student", "teacher", "other_teacher", "admin")}
    roles = {"owner": "student", "other_student": "student", "teacher": "teacher",
             "other_teacher": "teacher", "admin": "admin"}
    course_id, task_id, result_id, legacy_id = ObjectId(), ObjectId(), ObjectId(), ObjectId()
    try:
        db.users.insert_many([
            {"_id": oid, "name": name, "email": f"{name}-{run_id}@example.com", "role": roles[name],
             "password": "x", "createdAt": now}
            for name, oid in users.items()
        ])
        db.courses.insert_one({"_id": course_id, "name": "C", "teacherId": str(users["teacher"]), "createdAt": now})
        db.tasks.insert_one({"_id": task_id, "courseId": str(course_id), "sportId": str(ObjectId()),
                             "title": "T", "createdAt": now})
        base = {"taskId": str(task_id), "sportId": str(ObjectId()), "userId": str(users["owner"]),
                "attemptNo": 1, "pending": True, "status": "pending", "submittedAt": now, "testRun": run_id}
        db.video_results.insert_one({"_id": result_id, "courseId": str(course_id), **base})
        # Bản ghi cũ không có courseId: giáo viên được xác định qua task
        db.video_results.insert_one({"_id": legacy_id, **{**base, "attemptNo": 2}})

        client = TestClient(app)
        expected = {"owner": 200, "teacher": 200, "admin": 200, "other_student": 403, "other_teacher": 403}
        for rid, label in ((result_id, "có courseId"), (legacy_id, "không có courseId")):
            print(f"\n[TEST] Bài nộp {label}")
            for name, code in expected.items():
                headers = {"Authorization": f"Bearer {create_access_token({'sub': str(users[name])})}"}
                for path in (f"/api/video-results/{rid}", f"/api/video-results/{rid}/status",
                             f"/api/video-results/status/{rid}"):
                    resp = client.get(path, headers=headers)
                    assert resp.status_code == code, (name, path, resp.status_code, resp.text)
                    body = resp.json()
                    assert body["success"] is (code == 200) and body["code"] == code, body
                print(f"  ✓ {name}: {code}")

        resp = client.get(f"/api/video-results/{result_id}")
        assert resp.status_code == 401
        resp = client.get(f"/api/video-results/{ObjectId()}/status",
                          headers={"Authorization": f"Bearer {create_access_token({'sub': str(users['admin'])})}"})
        assert resp.status_code == 404
        print("\n  ✓ Không token → 401; resultId không tồn tại → 404; response giữ định dạng success/code/message/data")
    finally:
        db.users.delete_many({"_id": {"$in": list(users.values())}})
        db.courses.delete_one({"_id": course_id})
        db.tasks.delete_one({"_id": task_id})
        db.video_results.delete_many({"testRun": run_id})


if __name__ == "__main__":
    run()
    print("\n>>> TEST RESULT ACCESS PASSED")
