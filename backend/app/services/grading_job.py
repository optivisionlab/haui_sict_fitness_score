"""Grading job lưu trong outbox (video_results.gradingJob) và gửi qua Kafka tới AI worker.

Chỉ giữ những trường worker/AI thực sự dùng (~200 byte thay vì ~700 byte):
- jobId (= resultId): khóa job, dùng để cập nhật kết quả và chống chấm trùng
- sportCode, mode: định tuyến tới endpoint AI
- bucket, objectKey: AI tự tải video từ MinIO
- attemptNo: số lần nộp (log/AI)
- durationSec, fileSize: chọn làn small/large và tính timeout gọi AI
Thông tin task/course/user/detail đã có trong document video_results, không gửi lại.
"""

from typing import Any, Optional

JOB_SCHEMA_VERSION = 2

_JOB_FIELDS = (
    "jobId", "sportCode", "mode", "bucket", "objectKey", "attemptNo", "durationSec", "fileSize", "schemaVersion",
)


def build_grading_job(
    *,
    result_id: Any,
    sport_code: str,
    mode: str,
    bucket: str,
    object_key: str,
    attempt_no: int,
    duration_sec: Optional[float] = None,
    file_size: Optional[int] = None,
) -> dict[str, Any]:
    job: dict[str, Any] = {
        "jobId": str(result_id) if result_id is not None else None,
        "sportCode": str(sport_code).upper(),
        "mode": str(mode).upper(),
        "bucket": bucket,
        "objectKey": object_key,
        "attemptNo": int(attempt_no),
        "schemaVersion": JOB_SCHEMA_VERSION,
    }
    if duration_sec is not None:
        job["durationSec"] = duration_sec
    if file_size is not None:
        job["fileSize"] = int(file_size)
    return job


def compact_job(job: dict[str, Any]) -> dict[str, Any]:
    """Bỏ các trường thừa của job cũ (schema v1 lưu trước thay đổi này) trước khi gửi Kafka."""
    out = {key: job[key] for key in _JOB_FIELDS if job.get(key) is not None}
    if not out.get("jobId") and job.get("resultId"):
        out["jobId"] = str(job["resultId"])
    if not out.get("bucket") and job.get("minioBucket"):
        out["bucket"] = job["minioBucket"]
    return out
