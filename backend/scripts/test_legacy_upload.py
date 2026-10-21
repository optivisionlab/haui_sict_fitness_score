"""
Kiểm thử POST /video-results/upload (luồng cũ) không đọc cả video vào RAM.

1. Content-Length vượt LEGACY_UPLOAD_MAX_BYTES -> 413 trước khi đọc body (handler không chạy).
2. Service lấy dung lượng bằng seek/tell và stream file tạm lên MinIO, không gọi read() toàn bộ.
3. Stream thật 60MB lên MinIO (bucket test riêng): đỉnh bộ nhớ Python << 60MB.

    MONGODB_DB=fitness_score_test python scripts/test_legacy_upload.py
"""

import sys
import tempfile
import tracemalloc
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.core.config import settings
from app.crud.video_result import crud_video_result
from app.main import app
from app.services.minio_service import minio_service
from app.services.video_result_service import video_result_service


def test_early_rejection():
    print("\n[TEST 1] Content-Length vượt giới hạn → 413 trước khi đọc body")
    client = TestClient(app)
    with patch.object(settings, "LEGACY_UPLOAD_MAX_BYTES", 1000), \
         patch.object(video_result_service, "submit_video_file") as handler:
        resp = client.post(
            "/api/video-results/upload",
            files={"file": ("a.mp4", b"x" * 5000, "video/mp4")},
            data={"task_id": str(ObjectId())},
        )
    assert resp.status_code == 413, resp.text
    body = resp.json()
    assert body["success"] is False and body["code"] == 413 and body["data"] is None, body
    assert "upload-url" in body["message"], body
    assert not handler.called
    print(f"  ✓ 413, message: {body['message']}")


def test_service_streams_without_full_read():
    print("\n[TEST 2] Service stream file tạm, không read() toàn bộ")
    size = 3 * 1024 * 1024
    spooled = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
    spooled.write(b"v" * size)
    spooled.seek(0)
    reads = []
    original_read = spooled.read
    spooled.read = lambda *a, **k: reads.append(a) or original_read(*a, **k)
    upload = UploadFile(file=spooled, filename="clip.mp4", headers={"content-type": "video/mp4"})
    task = SimpleNamespace(course_id=str(ObjectId()), title="T", time_limit=None,
                           category=SimpleNamespace(value="practice"), grading_method=SimpleNamespace(value="highest"))
    created = SimpleNamespace(id=str(ObjectId()))
    calls = {}

    def fake_upload_file(file_data, object_name, length, content_type, bucket_name=None):
        calls.update(file_data=file_data, length=length, object_name=object_name)
        return f"videos/{object_name}"

    with patch.object(video_result_service, "_validate_submission_guards", return_value=(task, None, 1)), \
         patch.object(minio_service, "upload_file", side_effect=fake_upload_file), \
         patch.object(minio_service, "upload_bytes", side_effect=AssertionError("không được dùng upload_bytes")), \
         patch("app.services.video_result_service.crud_user.get", return_value=None), \
         patch("app.services.video_result_service.crud_sport.get", return_value=None), \
         patch("app.services.video_result_service.crud_video_result.create", return_value=created), \
         patch.object(type(crud_video_result), "collection", new_callable=PropertyMock, return_value=MagicMock()), \
         patch("app.services.video_result_service.notification_service.send_notification"):
        video_result_service.submit_video_file(str(ObjectId()), str(ObjectId()), str(ObjectId()), upload, 30)
    assert calls["file_data"] is spooled and calls["length"] == size, calls
    assert reads == [], f"read() bị gọi: {reads}"
    print(f"  ✓ Truyền file tạm ({size // (1024 * 1024)}MB) cho MinIO với length đúng, không read() trong service")

    with patch.object(settings, "LEGACY_UPLOAD_MAX_BYTES", 1024), \
         patch.object(video_result_service, "_validate_submission_guards", return_value=(task, None, 1)):
        spooled.seek(0)
        try:
            video_result_service.submit_video_file(str(ObjectId()), str(ObjectId()), str(ObjectId()), upload, 30)
            raise AssertionError("Không chặn file vượt giới hạn")
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 413, exc
    print("  ✓ Không có Content-Length (chunked) vẫn bị chặn ở service: 413")


def test_real_minio_streaming():
    print("\n[TEST 3] Stream thật 60MB lên MinIO")
    bucket = f"test-legacy-{uuid.uuid4().hex[:8]}"
    size = 60 * 1024 * 1024
    minio_service.client.make_bucket(bucket)
    try:
        with tempfile.TemporaryFile() as f:
            chunk = b"\0" * (1024 * 1024)
            for _ in range(size // len(chunk)):
                f.write(chunk)
            f.seek(0)
            tracemalloc.start()
            minio_service.upload_file(f, "big.mp4", length=size, bucket_name=bucket)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        stat = minio_service.client.stat_object(bucket, "big.mp4")
        assert stat.size == size, stat.size
        assert peak < 30 * 1024 * 1024, f"Đỉnh bộ nhớ {peak / 1e6:.0f}MB"
        print(f"  ✓ Upload 60MB, đỉnh bộ nhớ Python {peak / 1e6:.1f}MB (đọc cả file sẽ ≥ 60MB)")
    finally:
        for obj in minio_service.client.list_objects(bucket, recursive=True):
            minio_service.client.remove_object(bucket, obj.object_name)
        minio_service.client.remove_bucket(bucket)


if __name__ == "__main__":
    test_early_rejection()
    test_service_streams_without_full_read()
    test_real_minio_streaming()
    print("\n>>> TEST LEGACY UPLOAD PASSED")
