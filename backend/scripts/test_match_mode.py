"""
Kiểm thử bài quay đối kháng (mode MATCH, YOLO26s):
1. Giảng viên tạo bài: recording_mode / target_zone được chuẩn hóa.
2. Mode gửi AI: MATCH chỉ với bài đối kháng của môn quay video.
3. Job chấm giữ trường court qua outbox/Kafka (compact_job).
4. AI client: định tuyến MATCH và gửi court cho dịch vụ AI.
5. Upload: kiểm tra 4 điểm đánh dấu sân.
6. Điểm môn Pickleball từ metrics đối kháng khớp công thức (27) của dịch vụ AI.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.task import RecordingMode, TargetZone, grading_mode
from app.schemas.task import TeacherTaskUpsert
from app.schemas.video_result import VideoUploadUrlRequest
from app.services.ai_grading_client import AIGradingClient
from app.services.grading_job import build_grading_job, compact_job
from app.services.sports.pickleball import calculate_pickleball_score
from app.services.video_result_service import match_court

POINTS = [[0.24, 0.34], [0.72, 0.34], [0.66, 0.23], [0.27, 0.23]]


def test_teacher_upsert():
    print("[TEST 1] Giảng viên tạo bài đối kháng")
    t = TeacherTaskUpsert(title="Dink", recording_mode="match")
    assert t.recording_mode == RecordingMode.MATCH and t.target_zone == TargetZone.FULL
    t = TeacherTaskUpsert(title="Dink", recording_mode="match", target_zone="kitchen")
    assert t.target_zone == TargetZone.KITCHEN
    t = TeacherTaskUpsert(title="Giao bóng", target_zone="kitchen")
    assert t.recording_mode == RecordingMode.DIRECT and t.target_zone is None
    assert TeacherTaskUpsert.model_validate({"title": "x", "recordingMode": "match"}).recording_mode == RecordingMode.MATCH
    try:
        TeacherTaskUpsert(title="x", recording_mode="match", target_zone="everywhere")
        raise AssertionError("target_zone sai phải bị từ chối")
    except ValidationError:
        pass
    print("  ✓ match mặc định vùng full; direct bỏ target_zone; giá trị lạ bị từ chối")


def test_grading_mode_and_court():
    print("[TEST 2] Mode gửi AI và cấu hình sân")
    match_task = SimpleNamespace(recording_mode=RecordingMode.MATCH, target_zone=TargetZone.KITCHEN)
    direct_task = SimpleNamespace(recording_mode=None, target_zone=None)
    assert grading_mode(match_task, "video") == "MATCH"
    assert grading_mode(direct_task, "video") == "VIDEO"
    assert grading_mode(match_task, "camera") == "CAMERA"
    assert match_court(direct_task, POINTS) is None
    assert match_court(match_task, None) == {"target_zone": "kitchen", "student_side": "near"}
    assert match_court(match_task, POINTS)["points"] == POINTS
    print("  ✓ MATCH chỉ cho bài đối kháng quay video; dữ liệu cũ vẫn là VIDEO")


def test_job_keeps_court():
    print("[TEST 3] Job chấm giữ court")
    court = {"target_zone": "kitchen", "student_side": "near", "points": POINTS}
    job = build_grading_job(
        result_id="r1", sport_code="pickleball", mode="MATCH", bucket="b", object_key="k.mp4",
        attempt_no=1, duration_sec=30, file_size=10, court=court,
    )
    assert compact_job(job)["court"] == court and compact_job(job)["mode"] == "MATCH"
    plain = build_grading_job(result_id="r2", sport_code="PB", mode="VIDEO", bucket="b", object_key="k.mp4", attempt_no=1)
    assert "court" not in plain and "court" not in compact_job(plain)
    print("  ✓ court đi qua outbox/Kafka; bài trực diện không có court")


def test_ai_client():
    print("[TEST 4] AI client định tuyến MATCH")
    client = AIGradingClient(mock_mode=False)
    assert client.resolve_endpoint("PICKLEBALL", "MATCH") == (
        settings.AI_PICKLEBALL_MATCH_URL or settings.AI_PICKLEBALL_VIDEO_URL or settings.AI_API_URL
    )
    court = {"target_zone": "full", "student_side": "near", "points": POINTS}
    job = {"jobId": "r1", "sportCode": "PICKLEBALL", "mode": "MATCH", "bucket": "b", "objectKey": "k.mp4", "court": court}
    request = client.build_request(job)
    assert request["mode"] == "MATCH" and request["court"] == court
    assert "court" not in client.build_request({**job, "mode": "VIDEO"})

    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={
            "status": "completed", "mode": "MATCH", "score": 8.05, "feedback": "ok",
            "metrics": {"accuracy": 0.75, "hitCount": 15, "missCount": 5, "swingTotal": 20, "inCourtCount": 12,
                        "calibration": "court", "events": [{"time": 1.2, "result": "hit"}]},
        })

    async def run():
        client.bind_http_client(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        try:
            return await client.grade(job, timeout=5)
        finally:
            await client._http.aclose()

    result = asyncio.run(run())
    assert seen["court"] == court and seen["mode"] == "MATCH"
    assert result["aiScore"] == 8.05 and result["metrics"]["inCourtCount"] == 12
    print("  ✓ request có mode MATCH + court; kết quả giữ metrics đối kháng")


def test_upload_points():
    print("[TEST 5] Kiểm tra điểm đánh dấu sân khi upload")
    base = {"task_id": "t", "file_name": "a.mp4", "content_type": "video/mp4", "file_size": 10}
    assert VideoUploadUrlRequest(**base, court_points=POINTS).court_points == POINTS
    assert VideoUploadUrlRequest(**base).court_points is None
    for bad in ([[0.1, 0.1]] * 3, [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3], [1.4, 0.3]]):
        try:
            VideoUploadUrlRequest(**base, court_points=bad)
            raise AssertionError("court_points sai phải bị từ chối")
        except ValidationError:
            pass
    print("  ✓ đúng 4 điểm trong [0, 1]")


def test_score_matches_ai():
    print("[TEST 6] Công thức (27) với metrics đối kháng")
    metrics = {"accuracy": 0.75, "hitCount": 15, "missCount": 5, "swingTotal": 20, "inCourtCount": 12}
    assert calculate_pickleball_score(metrics) == 8.05
    print("  ✓ 7 x 0,75 + 2 x 1 + 12/15 = 8,05 (giống dịch vụ AI)")


if __name__ == "__main__":
    test_teacher_upsert()
    test_grading_mode_and_court()
    test_job_keeps_court()
    test_ai_client()
    test_upload_points()
    test_score_matches_ai()
    print("\n>>> TEST MATCH MODE PASSED")
