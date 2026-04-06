"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Fitness Score API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""

    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None = None
    REDIS_DECODE_RESPONSES: bool = True
    REDIS_NOTIFY_EVENTS: str = "KEA"

    # MinIO
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str

    # JWT
    SECRET_KEY: str = "a8f12d9d8b4f5f3f4e7d81e4a2f9d8a3fbd7c23ac4e6b5e13e7d95b0a1e6d8c9"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # External services
    EXTERNAL_TRACKING_API_URL: str = "http://10.100.200.119:8001/track_batch"

    @property
    def DATABASE_URL(self) -> str:
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg2://{user}:{password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
