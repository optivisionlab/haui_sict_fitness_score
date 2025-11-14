from pydantic_settings import BaseSettings
from functools import lru_cache
from urllib.parse import quote_plus


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fitness Score API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration (the new values)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    # Redis configuration
    REDIS_HOST: str = "10.100.200.119"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_DECODE_RESPONSES: bool = True
    # Redis server notify-keyspace-events config string. Example values:
    # - "Eh"  : publish keyevent notifications for hash events (hset/hdel)
    # - "KEA" : publish keyspace and keyevent notifications for all event types
    # Default is conservative (hash keyevents + generic events may be added by env).
    REDIS_NOTIFY_EVENTS: str = "KEA"

    @property
    def DATABASE_URL(self) -> str:
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg2://{user}:{password}@{self.POSTGRES_SERVER}"
            f":{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    SECRET_KEY: str = "a8f12d9d8b4f5f3f4e7d81e4a2f9d8a3fbd7c23ac4e6b5e13e7d95b0a1e6d8c9"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        
@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
