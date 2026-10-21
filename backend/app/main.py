import asyncio
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Awaitable, Callable

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core import (
    get_db,
    settings,
    setup_exception_handlers,
    setup_middlewares,
)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def init_db_indexes():
    """Tạo index MongoDB. Lỗi kết nối/tạo index được để nổi lên để app không khởi động."""
    database = get_db()
    database.command("ping")

    database.users.create_index("email", unique=True)
    database.users.create_index("userCode", unique=True, sparse=True)

    # Dọn dẹp index cũ dạng snake_case nếu có
    try:
        for idx in database.enrollments.list_indexes():
            if "user_id" in idx["name"] or "course_id" in idx["name"]:
                database.enrollments.drop_index(idx["name"])
                logger.info("Dropped stale index on enrollments: %s", idx["name"])
    except Exception as drop_err:
        logger.warning("Could not drop stale enrollments indexes: %s", drop_err)

    # Tự động đồng bộ các trường snake_case sang camelCase nếu có dữ liệu cũ
    try:
        for doc in database.enrollments.find({"userId": {"$exists": False}, "user_id": {"$exists": True}}):
            database.enrollments.update_one(
                {"_id": doc["_id"]},
                {"$set": {"userId": doc["user_id"], "courseId": doc["course_id"]}}
            )
        for doc in database.users.find({"userCode": {"$exists": False}, "user_code": {"$exists": True}}):
            database.users.update_one(
                {"_id": doc["_id"]},
                {"$set": {"userCode": doc["user_code"]}}
            )
        for doc in database.tasks.find({"courseId": {"$exists": False}, "course_id": {"$exists": True}}):
            update_fields = {"courseId": doc["course_id"]}
            if doc.get("sport_id") is not None:
                update_fields["sportId"] = doc["sport_id"]
            database.tasks.update_one(
                {"_id": doc["_id"]},
                {"$set": update_fields}
            )
        for doc in database.courses.find({"teacherId": {"$exists": False}, "teacher_id": {"$exists": True}}):
            database.courses.update_one(
                {"_id": doc["_id"]},
                {"$set": {"teacherId": doc["teacher_id"]}}
            )
    except Exception as mig_err:
        logger.warning("Could not migrate legacy fields: %s", mig_err)

    database.enrollments.create_index([("userId", 1), ("status", 1)])
    database.enrollments.create_index([("userId", 1), ("courseId", 1)], unique=True)
    database.enrollments.create_index([("courseId", 1), ("studentCode", 1)])

    database.courses.create_index([("teacherId", 1), ("status", 1)])
    database.tasks.create_index([("courseId", 1), ("category", 1)])
    database.sports.create_index("code", unique=True)

    database.video_results.create_index([("taskId", 1), ("userId", 1), ("attemptNo", 1)], unique=True)
    database.video_results.create_index([("taskId", 1), ("userId", 1), ("submittedAt", -1)])
    database.video_results.create_index([("pending", 1), ("submittedAt", 1)])
    database.video_results.create_index([("gradingJobStatus", 1), ("gradingJobNextAttemptAt", 1)])
    database.video_upload_sessions.create_index("expiresAt", expireAfterSeconds=0)

    database.live_results.create_index([("taskId", 1), ("userId", 1)])
    database.live_results.create_index([("cameraId", 1), ("startedAt", -1)])

    database.notifications.create_index([("userId", 1), ("isRead", 1), ("createdAt", -1)])


def _register_stop(stack: AsyncExitStack, name: str, stop: Callable[[], Awaitable[None]]) -> None:
    """Đăng ký hàm dừng vào stack; log thứ tự dừng và không để lỗi dừng làm hỏng shutdown."""

    async def _stop() -> None:
        logger.info("Stopping %s", name)
        try:
            await stop()
        except Exception as exc:
            logger.warning("Error stopping %s: %s", name, exc)
        else:
            logger.info("Stopped %s", name)

    stack.push_async_callback(_stop)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.ai_grading_client import ai_grading_client
    from app.services.ai_worker_pool import build_default_pools
    from app.services.grading_outbox import grading_outbox_dispatcher
    from app.services.kafka_consumer import kafka_result_consumer
    from app.services.kafka_producer import kafka_producer
    from app.services.minio_service import minio_service
    from app.services.sport_service import sport_service

    app.state.ready = False
    app.state.components = {
        "mongo": "starting",
        "minio": "starting",
        "kafka": "starting",
        "result_consumer": "disabled",
        "ai_worker": "disabled",
        "outbox": "starting",
    }
    components = app.state.components
    app.state.worker_pools = []

    async with AsyncExitStack() as stack:
        # 1. Hạ tầng bắt buộc: lỗi thì exception nổi lên, app không khởi động
        await asyncio.to_thread(init_db_indexes)
        await asyncio.to_thread(sport_service.sync_sports_from_definitions)
        components["mongo"] = "ok"
        await asyncio.to_thread(minio_service.ensure_bucket)
        components["minio"] = "ok"

        # 2. HTTP client dùng chung cho các lời gọi AI
        http_client = httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT_SECONDS)
        app.state.http_client = http_client
        ai_grading_client.bind_http_client(http_client)
        _register_stop(stack, "http client", http_client.aclose)

        # 3. Kafka producer: tùy chọn, lỗi thì chạy ở chế độ degraded (outbox dùng direct fallback)
        await kafka_producer.start()
        if kafka_producer.is_ready:
            _register_stop(stack, "kafka producer", kafka_producer.stop)
            components["kafka"] = "ok"
        else:
            components["kafka"] = "degraded"
            logger.warning(
                "Kafka unavailable at %s; running degraded (direct fallback=%s)",
                settings.KAFKA_BOOTSTRAP_SERVERS,
                settings.AI_DIRECT_FALLBACK,
            )

        if components["kafka"] == "ok":
            # 4. Result consumer
            await kafka_result_consumer.start()
            _register_stop(stack, "result consumer", kafka_result_consumer.stop)
            components["result_consumer"] = "ok" if kafka_result_consumer.is_running else "error"

            # 5. AI worker pool
            if settings.AI_WORKER_ENABLED:
                components["ai_worker"] = "ok"
                for pool in build_default_pools():
                    try:
                        await pool.start()
                    except Exception as exc:
                        logger.warning("Could not start AI worker pool %s: %s", pool.name, exc)
                        components["ai_worker"] = "error"
                        continue
                    _register_stop(stack, f"ai worker pool {pool.name}", pool.stop)
                    app.state.worker_pools.append(pool)

        # 6. Outbox dispatcher khởi động cuối cùng, sau khi bên nhận việc đã sẵn sàng
        await grading_outbox_dispatcher.start()
        _register_stop(stack, "outbox dispatcher", grading_outbox_dispatcher.stop)
        components["outbox"] = "ok"

        app.state.ready = True
        logger.info("Application ready: %s", components)
        try:
            yield
        finally:
            app.state.ready = False
            logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_TITLE,
    version="1.0.0",
    description="API Chấm điểm Thể dục & Quản lý Đào tạo thông minh",
    lifespan=lifespan,
)

setup_middlewares(app)
setup_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_TITLE}


@app.get("/health/ready", tags=["Health"])
def readiness_check(request: Request):
    """Readiness: 503 khi app chưa khởi động xong hoặc đang tắt."""
    from app.services.kafka_producer import kafka_producer

    state = request.app.state
    ready = bool(getattr(state, "ready", False))
    components = dict(getattr(state, "components", {}))
    if ready and components.get("kafka") == "ok" and not kafka_producer.is_ready:
        components["kafka"] = "degraded"
    pools = {pool.name: pool.health() for pool in getattr(state, "worker_pools", [])}
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "components": components, "worker_pools": pools},
    )
