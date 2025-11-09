from pydantic_settings import BaseSettings
from functools import lru_cache

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
    
    @property
    def DATABASE_URL(self) -> str:
    
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    SECRET_KEY: str = "a8f12d9d8b4f5f3f4e7d81e4a2f9d8a3fbd7c23ac4e6b5e13e7d95b0a1e6d8c9"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    print(Settings())
    return Settings()

settings = get_settings()
