import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

CFG_YAML = BASE_DIR / "src" / "config" / "config.yml"
if CFG_YAML.exists():
    with open(CFG_YAML, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
else:
    config = {}


def env(name, default=None, cast=None):
    value = os.getenv(name)
    if value is None or value == "":
        value = default
    if cast is not None and value is not None:
        return cast(value)
    return value


def as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def yaml_get(*keys, default=None):
    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _parse_camera_url_mapping(raw_value: str):
    mapping = {}
    if not raw_value:
        return mapping

    pairs = [item.strip() for item in str(raw_value).split(",") if item.strip()]
    for pair in pairs:
        if "=" not in pair:
            continue
        cam_id, url = pair.split("=", 1)
        cam_id = cam_id.strip()
        url = url.strip()
        if cam_id and url:
            mapping[str(cam_id)] = url
    return mapping


def _parse_int_list(raw_value: str):
    if not raw_value:
        return []
    return [int(item.strip()) for item in str(raw_value).split(",") if item.strip()]


def build_postgres_dsn(user: str, password: str, host: str, port: int, database: str) -> str:
    encoded_password = quote_plus(password or "")
    return f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{database}"


SEARCH_API_URL = str(
    env("SEARCH_API_URL", yaml_get("SEARCH_CONFIG", "url", default="http://127.0.0.1:8000"))
).rstrip("/")

SEARCH_API_CAMERA_URLS = _parse_camera_url_mapping(env("SEARCH_API_CAMERA_URLS", ""))


def get_search_api_url(cam_id=None):
    if cam_id is None:
        return SEARCH_API_URL
    return SEARCH_API_CAMERA_URLS.get(str(cam_id), SEARCH_API_URL)


KAFKA_SERVERS = env("KAFKA_SERVERS", yaml_get("KAFKA", "servers", default="127.0.0.1:9092"))
KAFKA_TOPIC_TEMPLATE = env("KAFKA_TOPIC_TEMPLATE", "camera-{cid}")

QDRANT_COLLECTION = env("QDRANT_COLLECTION", yaml_get("DATABASE", "qdrant_collection", default="face"))
LINE_BEGIN_SEARCH = float(env("LINE_BEGIN_SEARCH", yaml_get("SEARCH_CONFIG", "line_begin_search", default=0.5)))

REDIS_HOST = env("REDIS_HOST", yaml_get("REDIS", "REDIS_HOST", default="127.0.0.1"))
REDIS_PORT = int(env("REDIS_PORT", yaml_get("REDIS", "REDIS_PORT", default=6379)))
REDIS_DB = int(env("REDIS_DB", yaml_get("REDIS", "REDIS_DB", default=0)))
REDIS_PASSWORD = env("REDIS_PASSWORD", yaml_get("REDIS", "REDIS_PASSWORD", default=""))

POSTGRE_USER = env("POSTGRE_USER", yaml_get("POSTGRE", "user", default="postgres"))
POSTGRE_PASSWORD = env("POSTGRE_PASSWORD", yaml_get("POSTGRE", "password", default=""))
POSTGRE_HOST = env("POSTGRE_HOST", yaml_get("POSTGRE", "host", default="127.0.0.1"))
POSTGRE_PORT = int(env("POSTGRE_PORT", yaml_get("POSTGRE", "port", default=5432)))
POSTGRE_DB = env("POSTGRE_DB", yaml_get("POSTGRE", "database", default="postgres"))
POSTGRE_DSN = build_postgres_dsn(
    POSTGRE_USER,
    POSTGRE_PASSWORD,
    POSTGRE_HOST,
    POSTGRE_PORT,
    POSTGRE_DB,
)

MINIO_ENDPOINT = env(
    "MINIO_ENDPOINT",
    yaml_get("MINIO", "MINIO_ENDPOINT", default=yaml_get("MINIO", "MINIO_ENPOINT", default="127.0.0.1:9000")),
)
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", yaml_get("MINIO", "MINIO_ACCESS_KEY", default=""))
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", yaml_get("MINIO", "MINIO_SECRET_KEY", default=""))
MINIO_BUCKET_NAME = env("MINIO_BUCKET_NAME", yaml_get("MINIO", "MINIO_BUCKET_NAME", default=""))

TEST_MODE = as_bool(env("TEST_MODE", False))

YOLO_MODEL_PATH = env("YOLO_MODEL_PATH", yaml_get("YOLO_TRACKING", "model", default="weights/yolo11n.pt"))
TRACKING_CONF = float(env("TRACKING_CONF", yaml_get("YOLO_TRACKING", "conf", default=0.65)))
TRACKING_IOU = float(env("TRACKING_IOU", yaml_get("YOLO_TRACKING", "iou", default=0.8)))
SAVE_TRACKING = as_bool(env("SAVE_TRACKING", yaml_get("YOLO_TRACKING", "save_results", default=False)))

API_HANDLER_USER_COOLDOWN_MS = int(env("API_HANDLER_USER_COOLDOWN_MS", 10))
API_HANDLER_CAM_CALL_MIN_INTERVAL_MS = int(env("API_HANDLER_CAM_CALL_MIN_INTERVAL_MS", 3))
API_HANDLER_BAND_RATIO = float(env("API_HANDLER_BAND_RATIO", 0.06))
SEARCH_API_CROP_MODE = env("SEARCH_API_CROP_MODE", "none")

SAVE_DB_API_HOST = env("SAVE_DB_API_HOST", "localhost")
SAVE_DB_API_PORT = int(env("SAVE_DB_API_PORT", 8001))

CAM_IDS = _parse_int_list(env("CAM_IDS", "1,2,3,4"))
CAMERA_SOURCE_URLS = _parse_camera_url_mapping(env("CAMERA_SOURCE_URLS", ""))
START_BARRIER_TIMEOUT_SEC = int(env("START_BARRIER_TIMEOUT_SEC", 30))
CALL_ZONE_X1_RATIO = float(env("CALL_ZONE_X1_RATIO", 0.0))
CALL_ZONE_Y1_RATIO = float(env("CALL_ZONE_Y1_RATIO", 0.5))
CALL_ZONE_X2_RATIO = float(env("CALL_ZONE_X2_RATIO", 1.0))
CALL_ZONE_Y2_RATIO = float(env("CALL_ZONE_Y2_RATIO", 1.0))
CALL_ZONE_MIN_OVERLAP_RATIO = float(env("CALL_ZONE_MIN_OVERLAP_RATIO", 0.7))


@dataclass(frozen=True)
class EvalConfig:
    upload_each_checkin: bool = True
    checkin_cooldown_ms: int = 10
    lap_lock_seconds: int = 0


EVAL_CONFIG = EvalConfig(
    upload_each_checkin=as_bool(env("EVAL_UPLOAD_EACH_CHECKIN", True)),
    checkin_cooldown_ms=int(env("EVAL_CHECKIN_COOLDOWN_MS", 10)),
    lap_lock_seconds=int(env("EVAL_LAP_LOCK_SECONDS", 0)),
)