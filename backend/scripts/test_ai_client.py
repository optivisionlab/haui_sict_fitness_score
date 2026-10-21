"""
Kiểm thử AIGradingClient (T2):
1. Dùng chung HTTP client: 10 job chỉ mở 1 kết nối TCP tới AI.
2. Timeout truyền theo từng request.
3. Giữ nguyên phân loại lỗi retryable.
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from bson import ObjectId

from app.core.config import settings
from app.services.ai_grading_client import AIGradingClient, AIGradingError
from fake_ai_server import FakeAIServer


def make_job(title: str = "ok") -> dict:
    rid = str(ObjectId())
    return {
        "jobId": rid,
        "resultId": rid,
        "taskId": str(ObjectId()),
        "courseId": str(ObjectId()),
        "sportId": str(ObjectId()),
        "sportCode": "PICKLEBALL",
        "mode": "VIDEO",
        "userId": str(ObjectId()),
        "bucket": "videos",
        "objectKey": f"submissions/test/{rid}.mp4",
        "attemptNo": 1,
        "detail": {"title": title},
    }


async def run():
    server = await FakeAIServer().start()
    client = AIGradingClient(mock_mode=False)
    http = httpx.AsyncClient(timeout=30)
    client.bind_http_client(http)
    presign = patch(
        "app.services.minio_service.minio_service.get_presigned_url",
        return_value="http://minio.test/videos/x.mp4?sig",
    )
    try:
        with presign, patch.object(settings, "AI_PICKLEBALL_VIDEO_URL", server.url):
            print("\n[TEST 1] 10 job tuần tự dùng chung HTTP client")
            for _ in range(10):
                result = await client.grade(make_job())
                assert result["status"] == "completed" and result["aiScore"] == 8.0, result
            assert server.requests == 10, server.requests
            assert server.connections == 1, f"Mở {server.connections} kết nối cho 10 job"
            print(f"  ✓ 10 request, {server.connections} kết nối TCP")

            print("\n[TEST 2] Timeout truyền theo từng request")
            started = time.monotonic()
            try:
                await client.grade(make_job("sleep:3"), timeout=0.5)
                raise AssertionError("Không bị timeout")
            except AIGradingError as exc:
                elapsed = time.monotonic() - started
                assert exc.code == "ai_unreachable" and exc.retryable, exc.code
                assert elapsed < 2.0, elapsed
                print(f"  ✓ timeout=0.5s -> ai_unreachable (retryable) sau {elapsed:.2f}s")
            result = await client.grade(make_job("sleep:1"), timeout=5)
            assert result["status"] == "completed"
            print("  ✓ timeout=5s với job 1s -> completed")

            print("\n[TEST 3] Phân loại lỗi retryable")
            cases = {500: True, 503: True, 408: True, 429: True, 400: False, 422: False}
            for code, retryable in cases.items():
                try:
                    await client.grade(make_job(f"status:{code}"))
                    raise AssertionError(f"HTTP {code} không ném lỗi")
                except AIGradingError as exc:
                    assert exc.code == f"ai_http_{code}" and exc.retryable is retryable, (code, exc.code, exc.retryable)
            print(f"  ✓ {', '.join(f'{c}→{r}' for c, r in cases.items())}")
            try:
                await client.grade(make_job("busy:1"))
                raise AssertionError("429 không ném lỗi")
            except AIGradingError as exc:
                assert exc.code == "ai_http_429" and exc.busy and exc.retry_after == 1.0, (exc.code, exc.retry_after)
            try:
                await client.grade(make_job("status:429"))
            except AIGradingError as exc:
                assert not exc.busy, "429 không có Retry-After không phải trạng thái bận"
            print("  ✓ 429 + Retry-After → busy (retry_after=1s); 429 không có header → lỗi tạm thời thường")

            with patch.object(settings, "AI_PICKLEBALL_VIDEO_URL", "http://127.0.0.1:1/x"):
                try:
                    await client.grade(make_job())
                except AIGradingError as exc:
                    assert exc.code == "ai_unreachable" and exc.retryable
            job = make_job()
            job["sportCode"] = "RUNNING"
            try:
                await client.grade(job)
            except AIGradingError as exc:
                assert exc.code == "unsupported_route" and not exc.retryable
            print("  ✓ AI không kết nối được → ai_unreachable (retryable); RUNNING → unsupported_route")
    finally:
        await http.aclose()
        await server.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("\n>>> TEST AI CLIENT PASSED")
