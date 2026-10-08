import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")


class Settings:
    APP_TITLE: str = "Lab Fitness API"

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

    # AI / Worker Auth
    AI_API_KEY: str = os.getenv("AI_API_KEY", "internal-ai-worker-secret-key")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_GRADING_JOBS: str = os.getenv("KAFKA_TOPIC_GRADING_JOBS", "video-grading-jobs")
    KAFKA_TOPIC_GRADING_RESULTS: str = os.getenv("KAFKA_TOPIC_GRADING_RESULTS", "video-grading-results")
    KAFKA_TOPIC_GRADING_DLQ: str = os.getenv("KAFKA_TOPIC_GRADING_DLQ", "video-grading-dlq")
    KAFKA_CONSUMER_GROUP_BACKEND: str = os.getenv("KAFKA_CONSUMER_GROUP_BACKEND", "backend-result-consumer")
    KAFKA_CONSUMER_GROUP_AI: str = os.getenv("KAFKA_CONSUMER_GROUP_AI", "ai-grading-worker")

    # CORS
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200").split(",")
        if o.strip()
    ]


settings = Settings()
