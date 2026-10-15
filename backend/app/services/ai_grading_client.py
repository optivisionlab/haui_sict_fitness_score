from typing import Any

import httpx

from app.core.config import settings


class AIGradingClient:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = settings.AI_MOCK_MODE if mock_mode is None else mock_mode

    @staticmethod
    def build_request(job: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": job.get("jobId") or job.get("job_id"),
            "result_id": job.get("resultId") or job.get("result_id"),
            "task_id": job.get("taskId") or job.get("task_id"),
            "course_id": job.get("courseId") or job.get("course_id"),
            "sport_id": job.get("sportId") or job.get("sport_id"),
            "sport_code": job.get("sportCode") or job.get("sport_code"),
            "mode": job.get("mode"),
            "bucket": job.get("bucket") or job.get("minioBucket"),
            "object_key": job.get("objectKey") or job.get("object_key"),
            "video_url": job.get("videoUrl") or job.get("video_url"),
            "minio_endpoint": job.get("minioEndpoint") or settings.MINIO_ENDPOINT,
            "user_id": job.get("userId") or job.get("user_id"),
            "attempt": job.get("attemptNo") or job.get("attempt"),
            "schema_version": job.get("schemaVersion") or job.get("schema_version", 1),
            "detail": job.get("detail"),
        }

    async def grade(self, job: dict[str, Any]) -> dict[str, Any]:
        request_data = self.build_request(job)
        if self.mock_mode:
            return {
                "jobId": request_data["job_id"],
                "resultId": request_data["result_id"],
                "sportCode": request_data["sport_code"],
                "mode": request_data["mode"],
                "status": "completed",
                "aiScore": 8.5,
                "aiComment": "Bài tập được thực hiện đạt yêu cầu.",
                "metrics": {"accuracy": 0.85},
            }

        if not settings.AI_API_URL:
            raise RuntimeError("AI_API_URL is required when AI_MOCK_MODE is disabled")

        headers = {"Authorization": f"Bearer {settings.AI_API_KEY}"} if settings.AI_API_KEY else {}
        async with httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.AI_API_URL, json=request_data, headers=headers)
            response.raise_for_status()
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