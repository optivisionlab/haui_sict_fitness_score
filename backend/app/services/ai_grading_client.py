from typing import Any

import httpx

from app.core.config import settings

# seed_data dùng code "PICKLE", sports/definitions dùng "PICKLEBALL"
PICKLEBALL_CODES = {"PICKLE", "PICKLEBALL"}


class AIGradingError(Exception):
    """Lỗi khi gọi AI. `retryable=False` nghĩa là lỗi vĩnh viễn (request sai, video không hợp lệ...)."""

    def __init__(self, code: str, retryable: bool, retry_after: float | None = None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        # AI báo đang bận (429/503 kèm Retry-After): chờ rồi gửi lại, không tính là một lần thất bại
        self.retry_after = retry_after

    @property
    def busy(self) -> bool:
        return self.retry_after is not None


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
    def build_request(job: dict[str, Any]) -> dict[str, Any]:
        """Request tối thiểu cho AI: AI chỉ cần job_id + bucket/object_key để tự tải video từ MinIO.

        Không gửi task/course/user/detail và không ký presigned URL (AI dùng credential MinIO riêng).
        """
        result_id = job.get("resultId") or job.get("result_id") or job.get("jobId") or job.get("job_id")
        job_id = job.get("jobId") or job.get("job_id") or result_id
        bucket = job.get("bucket") or job.get("minioBucket") or settings.MINIO_BUCKET_NAME
        object_key = job.get("objectKey") or job.get("object_key")
        if not job_id:
            raise AIGradingError("invalid_job_missing_job_id", retryable=False)
        if not object_key:
            raise AIGradingError("invalid_job_missing_object_key", retryable=False)
        if object_key.startswith(f"{bucket}/"):
            object_key = object_key[len(bucket) + 1:]

        request = {
            "job_id": str(job_id),
            "result_id": str(result_id),
            "bucket": bucket,
            "object_key": object_key,
            "mode": str(job.get("mode") or "VIDEO").upper(),
            "attempt": int(job.get("attemptNo") or job.get("attempt") or 1),
        }
        if settings.AI_MINIO_ENDPOINT:
            request["minio_endpoint"] = settings.AI_MINIO_ENDPOINT
        return request

    async def grade(self, job: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        request_data = self.build_request(job)
        if self.mock_mode:
            return {
                "resultId": request_data["result_id"],
                "status": "completed",
                "aiScore": 8.5,
                "aiComment": "Bài tập Pickleball đạt yêu cầu kỹ thuật cơ bản.",
                "metrics": {"accuracy": 0.85, "hitCount": 17, "missCount": 3},
            }

        endpoint = self.resolve_endpoint(job.get("sportCode") or job.get("sport_code"), request_data["mode"])
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
            retry_after = None
            if response.status_code in (429, 503):
                try:
                    retry_after = max(1.0, float(response.headers.get("Retry-After", "")))
                except ValueError:
                    retry_after = None
            raise AIGradingError(f"ai_http_{response.status_code}", retryable=retryable, retry_after=retry_after)

        body = response.json()
        # Kết quả gửi lên Kafka chỉ gồm trường backend dùng (không lặp score/aiScore, feedback/aiComment)
        return {
            "resultId": request_data["result_id"],
            "status": body.get("status", "completed"),
            "aiScore": body.get("aiScore", body.get("score")),
            "aiComment": body.get("aiComment", body.get("feedback")),
            "metrics": body.get("metrics") or {},
        }


ai_grading_client = AIGradingClient()
