"""
Kiểm thử lifespan (T1) bằng cách chạy uvicorn thật trong subprocess:
1. MinIO không truy cập được -> app thoát với lỗi rõ ràng.
2. Kafka không truy cập được -> app vẫn chạy, /health/ready báo kafka=degraded.
3. Hạ tầng đầy đủ -> ready, SIGTERM thì dừng đúng thứ tự, không có traceback.

Chạy với DB/topic riêng để không đụng dữ liệu thật:
    MONGODB_DB=fitness_score_test python scripts/test_lifespan.py
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKEND_DIR = Path(__file__).resolve().parent.parent
PORT = int(os.getenv("TEST_PORT", "8011"))
UNREACHABLE = "127.0.0.1:1"


def _env(**overrides: str) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("MONGODB_DB", "fitness_score_test")
    env.setdefault("KAFKA_TOPIC_GRADING_JOBS", "test-video-grading-jobs")
    env.setdefault("KAFKA_TOPIC_GRADING_RESULTS", "test-video-grading-results")
    env.setdefault("KAFKA_CONSUMER_GROUP_BACKEND", "test-backend-result-consumer")
    env.setdefault("KAFKA_CONSUMER_GROUP_AI", "test-ai-grading-worker")
    env.setdefault("AI_MOCK_MODE", "true")
    env.update(overrides)
    return env


def _start(env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _ready(timeout: float = 60.0) -> tuple[int, dict]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health/ready", timeout=2) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.5)
    raise TimeoutError("App không phản hồi /health/ready")


def _stop(proc: subprocess.Popen) -> str:
    proc.send_signal(signal.SIGTERM)
    out, _ = proc.communicate(timeout=60)
    return out


def test_minio_down_fails_fast():
    print("\n[TEST 1] MinIO không truy cập được -> app không khởi động")
    proc = _start(_env(MINIO_ENDPOINT=UNREACHABLE))
    try:
        out, _ = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        raise AssertionError("App vẫn chạy khi MinIO chết:\n" + out[-2000:])
    assert proc.returncode != 0, out[-2000:]
    assert "Application startup failed" in out, out[-2000:]
    print(f"  ✓ App thoát với mã {proc.returncode}, log có 'Application startup failed'")


def test_kafka_down_runs_degraded():
    print("\n[TEST 2] Kafka không truy cập được -> app chạy, kafka=degraded")
    proc = _start(_env(KAFKA_BOOTSTRAP_SERVERS=UNREACHABLE))
    try:
        status, body = _ready()
        assert status == 200, body
        components = body["components"]
        assert components["kafka"] == "degraded", components
        assert components["mongo"] == "ok" and components["minio"] == "ok", components
        assert components["ai_worker"] == "disabled", components
        assert components["outbox"] == "ok", components
        print(f"  ✓ /health/ready = 200, components={components}")
    finally:
        out = _stop(proc)
    assert "Traceback" not in out, out[-3000:]


def test_full_startup_and_shutdown_order():
    print("\n[TEST 3] Hạ tầng đầy đủ -> ready; SIGTERM dừng đúng thứ tự")
    proc = _start(_env())
    try:
        status, body = _ready()
        assert status == 200, body
        assert body["components"]["kafka"] == "ok", body
        print(f"  ✓ /health/ready = 200, components={body['components']}")
    finally:
        out = _stop(proc)

    assert "Traceback" not in out, out[-3000:]
    expected = ["outbox dispatcher", "ai worker pool default", "result consumer", "kafka producer", "http client"]
    positions = []
    for name in expected:
        marker = f"Stopping {name}"
        assert marker in out, f"Thiếu log '{marker}':\n{out[-3000:]}"
        positions.append(out.index(marker))
    assert positions == sorted(positions), f"Sai thứ tự dừng: {list(zip(expected, positions))}"
    print("  ✓ Thứ tự dừng: " + " → ".join(expected) + ", không có traceback")


if __name__ == "__main__":
    test_minio_down_fails_fast()
    test_kafka_down_runs_degraded()
    test_full_startup_and_shutdown_order()
    print("\n>>> TEST LIFESPAN PASSED")
