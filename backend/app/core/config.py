import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")


class Settings:
    APP_TITLE: str = "Lab Fitness API"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # MongoDB
    MONGODB_URI: str = os.getenv(
        "MONGODB_URI", "mongodb://127.0.0.1:27018/?authSource=admin"
    )
    MONGODB_DB: str = os.getenv("MONGODB_DB", "fitness_score")
    MONGODB_USERNAME: str | None = os.getenv("MONGODB_USERNAME") or os.getenv(
        "MONGO_ROOT_USERNAME"
    )
    MONGODB_PASSWORD: str | None = os.getenv("MONGODB_PASSWORD") or os.getenv(
        "MONGO_ROOT_PASSWORD"
    )

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))  # 7 days

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6380))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
    REDIS_DECODE_RESPONSES: bool = os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true"
    REDIS_NOTIFY_EVENTS: str = os.getenv("REDIS_NOTIFY_EVENTS", "KEA")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_PUBLIC_ENDPOINT: str | None = os.getenv("MINIO_PUBLIC_ENDPOINT")
    MINIO_ACCESS_KEY: str = os.getenv(
        "MINIO_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "admin")
    )
    MINIO_SECRET_KEY: str = os.getenv(
        "MINIO_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "password123")
    )
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "videos")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"
    # Dọn video đã upload nhưng không confirm (không có video_results) sau UPLOAD_ORPHAN_MAX_AGE_SEC
    UPLOAD_CLEANUP_ENABLED: bool = os.getenv("UPLOAD_CLEANUP_ENABLED", "true").lower() == "true"
    UPLOAD_CLEANUP_INTERVAL_SEC: float = float(os.getenv("UPLOAD_CLEANUP_INTERVAL_SEC", "3600"))
    UPLOAD_ORPHAN_MAX_AGE_SEC: float = float(os.getenv("UPLOAD_ORPHAN_MAX_AGE_SEC", "86400"))

    # AI / Worker Auth
    AI_API_KEY: str = os.getenv("AI_API_KEY", "internal-ai-worker-secret-key")
    AI_API_URL: str = os.getenv("AI_API_URL", "http://0.0.0.0:8888/api/v1/process")
    AI_PICKLEBALL_VIDEO_URL: str = os.getenv(
        "AI_PICKLEBALL_VIDEO_URL", "http://0.0.0.0:8888/api/v1/process"
    )
    # AI xử lý video đồng bộ trong 1 request nên cần timeout dài
    AI_API_TIMEOUT_SECONDS: float = float(os.getenv("AI_API_TIMEOUT_SECONDS", "600"))
    AI_ROUTER_ENABLED: bool = os.getenv("AI_ROUTER_ENABLED", "true").lower() == "true"
    AI_MOCK_MODE: bool = os.getenv("AI_MOCK_MODE", "false").lower() == "true"
    AI_WORKER_ENABLED: bool = os.getenv("AI_WORKER_ENABLED", "true").lower() == "true"
    # Số request đồng thời tối đa tới AI (theo sức GPU), dùng chung mọi pool trong process
    AI_MAX_CONCURRENCY: int = int(os.getenv("AI_MAX_CONCURRENCY", "3"))
    AI_WORKER_SHUTDOWN_GRACE: float = float(os.getenv("AI_WORKER_SHUTDOWN_GRACE", "30"))
    AI_MAX_RETRIES: int = int(os.getenv("AI_MAX_RETRIES", "3"))
    # 2 làn theo thời lượng video: video dài không chặn video ngắn
    AI_LANE_THRESHOLD_SEC: float = float(os.getenv("AI_LANE_THRESHOLD_SEC", "90"))
    AI_POOL_SMALL_CONCURRENCY: int = int(os.getenv("AI_POOL_SMALL_CONCURRENCY", "2"))
    AI_POOL_LARGE_CONCURRENCY: int = int(os.getenv("AI_POOL_LARGE_CONCURRENCY", "1"))
    # Timeout gọi AI = min(BASE + PER_VIDEO_SEC x durationSec, MAX); thiếu durationSec thì dùng AI_API_TIMEOUT_SECONDS
    AI_TIMEOUT_BASE_SEC: float = float(os.getenv("AI_TIMEOUT_BASE_SEC", "60"))
    AI_TIMEOUT_PER_VIDEO_SEC: float = float(os.getenv("AI_TIMEOUT_PER_VIDEO_SEC", "4"))
    AI_TIMEOUT_MAX_SEC: float = float(os.getenv("AI_TIMEOUT_MAX_SEC", "1800"))
    # Gọi thẳng AI khi Kafka không sẵn sàng (outbox fallback)
    AI_DIRECT_FALLBACK: bool = os.getenv("AI_DIRECT_FALLBACK", "true").lower() == "true"
    # MinIO endpoint mà AI service dùng để tải video (phải truy cập được từ máy chạy AI)
    AI_MINIO_ENDPOINT: str = (
        os.getenv("AI_MINIO_ENDPOINT")
        or os.getenv("MINIO_PUBLIC_ENDPOINT")
        or os.getenv("MINIO_ENDPOINT", "localhost:9000")
    )

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_GRADING_JOBS: str = os.getenv("KAFKA_TOPIC_GRADING_JOBS", "video-grading-jobs")
    KAFKA_TOPIC_GRADING_JOBS_SMALL: str = os.getenv("KAFKA_TOPIC_GRADING_JOBS_SMALL", "video-grading-jobs-small")
    KAFKA_TOPIC_GRADING_JOBS_LARGE: str = os.getenv("KAFKA_TOPIC_GRADING_JOBS_LARGE", "video-grading-jobs-large")
    KAFKA_TOPIC_GRADING_RESULTS: str = os.getenv("KAFKA_TOPIC_GRADING_RESULTS", "video-grading-results")
    KAFKA_TOPIC_GRADING_DLQ: str = os.getenv("KAFKA_TOPIC_GRADING_DLQ", "video-grading-dlq")
    KAFKA_CONSUMER_GROUP_BACKEND: str = os.getenv("KAFKA_CONSUMER_GROUP_BACKEND", "backend-result-consumer")
    KAFKA_CONSUMER_GROUP_AI: str = os.getenv("KAFKA_CONSUMER_GROUP_AI", "ai-grading-worker")
    KAFKA_CONSUMER_GROUP_ROUTER: str = os.getenv("KAFKA_CONSUMER_GROUP_ROUTER", "backend-ai-router")

    # CORS
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
        if o.strip()
    ]


settings = Settings()
