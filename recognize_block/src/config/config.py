import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

CFG_YAML = BASE_DIR / "src" / "config" / "config.yml"
with open(CFG_YAML, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f) or {}

def env(name, default=None, cast=None):
    v = os.getenv(name, default)
    if cast and v is not None:
        return cast(v)
    return v


def _parse_camera_url_mapping(raw_value: str):
    mapping = {}
    if not raw_value:
        return mapping

    pairs = [item.strip() for item in raw_value.split(",") if item.strip()]
    for pair in pairs:
        if "=" not in pair:
            continue

        cam_id, url = pair.split("=", 1)
        cam_id = cam_id.strip()
        url = url.strip().rstrip("/")

        if cam_id and url:
            mapping[str(cam_id)] = url

    return mapping


SEARCH_API_URL = env(
    "SEARCH_API_URL",
    config.get("SEARCH_CONFIG", {}).get("url", "http://127.0.0.1:8000"),
).rstrip("/")

SEARCH_API_CAMERA_URLS = _parse_camera_url_mapping(env("SEARCH_API_CAMERA_URLS", ""))


def get_search_api_url(cam_id=None):
    if cam_id is None:
        return SEARCH_API_URL
    return SEARCH_API_CAMERA_URLS.get(str(cam_id), SEARCH_API_URL)

# SEARCH_API_URL = env("SEARCH_API_URL", config.get("SEARCH_CONFIG", {}).get("url", "http://127.0.0.1:8000"))
KAFKA_SERVERS  = env("KAFKA_SERVERS",  config.get("KAFKA", {}).get("servers", "127.0.0.1:9092"))
QDRANT_COLLECTION = env("QDRANT_COLLECTION", config.get("DATABASE", {}).get("qdrant_collection", "face"))
LINE_BEGIN_SEARCH = float(env("LINE_BEGIN_SEARCH", config.get("SEARCH_CONFIG", {}).get("line_begin_search", 0.5)))

REDIS_HOST = env("REDIS_HOST", config.get("REDIS", {}).get("REDIS_HOST", "127.0.0.1"))
REDIS_PORT = int(env("REDIS_PORT", config.get("REDIS", {}).get("REDIS_PORT", 6379)))
REDIS_DB   = int(env("REDIS_DB",   config.get("REDIS", {}).get("REDIS_DB", 0)))
REDIS_PASSWORD = env("REDIS_PASSWORD", config.get("REDIS", {}).get("REDIS_PASSWORD", ""))

POSTGRE_USER = env("POSTGRE_USER", config.get("POSTGRE", {}).get("user", "postgres"))
POSTGRE_PASSWORD = env("POSTGRE_PASSWORD", config.get("POSTGRE", {}).get("password", ""))
POSTGRE_HOST = env("POSTGRE_HOST", config.get("POSTGRE", {}).get("host", "127.0.0.1"))
POSTGRE_PORT = int(env("POSTGRE_PORT", config.get("POSTGRE", {}).get("port", 5432)))
POSTGRE_DB   = env("POSTGRE_DB", config.get("POSTGRE", {}).get("database", "postgres"))

MINIO_ENDPOINT = env("MINIO_ENDPOINT", config.get("MINIO", {}).get("MINIO_ENPOINT", "127.0.0.1:9000"))
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", config.get("MINIO", {}).get("MINIO_ACCESS_KEY", ""))
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", config.get("MINIO", {}).get("MINIO_SECRET_KEY", ""))
MINIO_BUCKET_NAME = env("MINIO_BUCKET_NAME", config.get("MINIO", {}).get("MINIO_BUCKET_NAME", ""))

TEST_MODE = env("TEST_MODE", config.get("TEST_MODE", "False")).lower() == "true"

