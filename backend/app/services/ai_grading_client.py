import asyncio
from datetime import timedelta
from typing import Any

import httpx

from app.core.config import settings

# Thời hạn presigned GET URL gửi cho AI: đủ dài để AI xếp hàng + tải video
AI_VIDEO_URL_TTL = timedelta(hours=2)

# seed_data dùng code "PICKLE", sports/definitions dùng "PICKLEBALL"
PICKLEBALL_CODES = {"PICKLE", "PICKLEBALL"}


class AIGradingError(Exception):
    """Lỗi khi gọi AI. `retryable=False` nghĩa là lỗi vĩnh viễn (request sai, video không hợp lệ...)."""

    def __init__(self, code: str, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class AIGradingClient:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = settings.AI_MOCK_MODE if mock_mode is None else mock_mode
        self._http: httpx.AsyncClient | None = None

    def bind_http_client(self, client: httpx.AsyncClient | None) -> None:
        """Gắn HTTP client dùng chung (do lifespan tạo và đóng) để tái sử dụng kết nối tới AI."""
        self._http = client

    def _get_http(self) -> httpx.AsyncClient:
        # Ngoài lifespan (script, test) thì tự tạo 1 client và dùng lại cho các lần gọi sau
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT_SECONDS)
        return self._http

    def resolve_endpoint(self, sport_code: str | None, mode: str | None) -> str:
        """
        Định tuyến adapter tới endpoint AI phù hợp:
        - Môn Pickleball (code PICKLE/PICKLEBALL), mode VIDEO: AI_PICKLEBALL_VIDEO_URL
        - Môn/mode chưa có AI: lỗi unsupported_route, không đoán endpoint
        """
        code = str(sport_code or "").strip().upper()
        m = str(mode or "").strip().upper()

        if code in PICKLEBALL_CODES and m == "VIDEO":
            return settings.AI_PICKLEBALL_VIDEO_URL or settings.AI_API_URL

        raise AIGradingError("unsupported_route", retryable=False)

    @staticmethod
    def _build_detail(detail: Any) -> dict[str, str]:
        """AI yêu cầu detail = {title, category, gradingMethod, timeLimit}, tất cả là chuỗi."""
        if not isinstance(detail, dict):
            detail = {"title": detail} if detail else {}
        return {
            key: "" if detail.get(key) is None else str(detail.get(key))
            for key in ("title", "category", "gradingMethod", "timeLimit")
        }

    @staticmethod
    def build_request(job: dict[str, Any]) -> dict[str, Any]:
        """Chuyển job (camelCase, lưu trong MongoDB/Kafka) sang request schema của AI API."""
        job_id = job.get("jobId") or job.get("job_id")
        result_id = job.get("resultId") or job.get("result_id")
        task_id = job.get("taskId") or job.get("task_id")
        course_id = job.get("courseId") or job.get("course_id")
        sport_id = job.get("sportId") or job.get("sport_id")
        sport_code = str(job.get("sportCode") or job.get("sport_code") or "").upper()
        mode = str(job.get("mode") or "").upper()
        bucket = job.get("bucket") or job.get("minioBucket") or settings.MINIO_BUCKET_NAME
        object_key = job.get("objectKey") or job.get("object_key")
        user_id = job.get("userId") or job.get("user_id")
        attempt = int(job.get("attemptNo") or job.get("attempt") or 1)

        if object_key and object_key.startswith(f"{bucket}/"):
            object_key = object_key[len(bucket) + 1:]

        required = {
            "job_id": job_id,
            "result_id": result_id,
            "task_id": task_id,
            "course_id": course_id,
            "sport_id": sport_id,
            "user_id": user_id,
            "object_key": object_key,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise AIGradingError(f"invalid_job_missing_{missing[0]}", retryable=False)

        # URL video trên MinIO (presigned GET) để AI có thể tải trực tiếp
        from app.services.minio_service import minio_service
        try:
            video_url = minio_service.get_presigned_url(
                object_key, expires=AI_VIDEO_URL_TTL, bucket_name=bucket
            )
        except Exception as exc:
            raise AIGradingError("minio_presign_failed", retryable=True) from exc

        return {
            "job_id": str(job_id),
            "result_id": str(result_id),
            "task_id": str(task_id),
            "course_id": str(course_id),
            "sport_id": str(sport_id),
            "sport_code": sport_code,
            "mode": mode,
            "bucket": bucket,
            "object_key": object_key,
            "video_url": video_url,
            "minio_endpoint": settings.AI_MINIO_ENDPOINT,
            "user_id": str(user_id),
            "attempt": attempt,
            "schema_version": int(job.get("schemaVersion") or job.get("schema_version") or 1),
            "detail": AIGradingClient._build_detail(job.get("detail")),
        }

    async def grade(self, job: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        # build_request ký presigned URL qua MinIO SDK (đồng bộ, lần đầu có gọi mạng lấy region)
        request_data = await asyncio.to_thread(self.build_request, job)
        if self.mock_mode:
            return {
                "jobId": request_data["job_id"],
                "resultId": request_data["result_id"],
                "sportCode": request_data["sport_code"],
                "mode": request_data["mode"],
                "status": "completed",
                "score": 8.5,
                "aiScore": 8.5,
                "feedback": "Bài tập Pickleball đạt yêu cầu kỹ thuật cơ bản.",
                "aiComment": "Bài tập Pickleball đạt yêu cầu kỹ thuật cơ bản.",
                "metrics": {"accuracy": 0.85, "hitCount": 17, "missCount": 3},
            }

        endpoint = self.resolve_endpoint(request_data["sport_code"], request_data["mode"])
        if not endpoint:
            raise AIGradingError("ai_endpoint_not_configured", retryable=False)

        headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"} if settings.AI_API_KEY else {}
        try:
            response = await self._get_http().post(
                endpoint,
                json=request_data,
                headers=headers,
                timeout=timeout if timeout is not None else settings.AI_API_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            # Timeout / không kết nối được AI: lỗi tạm thời, retry được
            raise AIGradingError("ai_unreachable", retryable=True) from exc

        if response.status_code >= 400:
            # 4xx (trừ 408/429) là lỗi vĩnh viễn: request/video không hợp lệ, retry vô ích
            retryable = response.status_code >= 500 or response.status_code in (408, 429)
            raise AIGradingError(f"ai_http_{response.status_code}", retryable=retryable)

        result = response.json()
        result.setdefault("jobId", request_data["job_id"])
        result.setdefault("resultId", request_data["result_id"])
        result.setdefault("status", "completed")
        if "aiScore" not in result and "score" in result:
            result["aiScore"] = result["score"]
        if "aiComment" not in result and "feedback" in result:
            result["aiComment"] = result["feedback"]
        return result


ai_grading_client = AIGradingClient()
