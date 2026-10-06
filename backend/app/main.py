import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api import api_router
from app.core import (
    get_db,
    settings,
    setup_exception_handlers,
    setup_middlewares,
)

logger = logging.getLogger(__name__)


def init_db_indexes():
    try:
        database = get_db()
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

        database.live_results.create_index([("taskId", 1), ("userId", 1)])
        database.live_results.create_index([("cameraId", 1), ("startedAt", -1)])

        database.notifications.create_index([("userId", 1), ("isRead", 1), ("createdAt", -1)])
    except Exception as e:
        logger.warning("Could not initialize MongoDB indexes: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_indexes()
    try:
        from app.services.sport_service import sport_service
        sport_service.sync_sports_from_definitions()
    except Exception as e:
        logger.warning("Could not auto-sync sport definitions: %s", e)
    try:
        from app.services.minio_service import minio_service
        minio_service.ensure_bucket()
    except Exception as e:
        logger.warning("Could not ensure MinIO bucket: %s", e)

    # Khởi động Kafka Producer & Consumer
    try:
        from app.services.kafka_producer import kafka_producer
        from app.services.kafka_consumer import kafka_result_consumer
        await kafka_producer.start()
        await kafka_result_consumer.start()
    except Exception as e:
        logger.warning("Could not initialize Kafka services: %s", e)

    yield

    # Dừng Kafka Producer & Consumer khi tắt app
    try:
        from app.services.kafka_producer import kafka_producer
        from app.services.kafka_consumer import kafka_result_consumer
        await kafka_result_consumer.stop()
        await kafka_producer.stop()
    except Exception as e:
        logger.warning("Error stopping Kafka services: %s", e)


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