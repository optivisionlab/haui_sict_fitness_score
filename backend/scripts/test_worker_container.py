"""
Kiểm thử AI worker chạy container riêng (APP_ROLE=worker) với API ở APP_ROLE=api.

1. API (local, APP_ROLE=api) không chạy worker pool; container worker không mount API.
2. Job do outbox của API publish được container worker chấm, result consumer của API lưu kết quả.
3. `docker stop` khi đang có job: drain job ngắn, hủy job dài sau grace, không traceback;
   container mới nhận lại job dài.

Cần image đã build:  docker build -t haui-fitness-backend:worker-test backend
    MONGODB_DB=fitness_score_test python scripts/test_worker_container.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_harness import FakeAIProcess, Pipeline

IMAGE = os.getenv("WORKER_IMAGE", "haui-fitness-backend:worker-test")
NETWORK = os.getenv("WORKER_NETWORK", "haui-fitness_app")
FAKE_AI_PORT = 18890


def docker(*args: str, check: bool = True) -> str:
    out = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and out.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)}: {out.stderr}")
    return out.stdout + out.stderr


class WorkerContainer:
    def __init__(self, pipe: Pipeline, name: str):
        self.name = name
        self.env = {
            "APP_ROLE": "worker",
            "LOG_LEVEL": "INFO",
            "MONGODB_URI": "mongodb://mongodb:27017/?authSource=admin",
            "MONGODB_USERNAME": os.environ["MONGO_ROOT_USERNAME"],
            "MONGODB_PASSWORD": os.environ["MONGO_ROOT_PASSWORD"],
            "MONGODB_DB": pipe.env["MONGODB_DB"],
            "MINIO_ENDPOINT": "minio:9000",
            "MINIO_ACCESS_KEY": os.environ["MINIO_ROOT_USER"],
            "MINIO_SECRET_KEY": os.environ["MINIO_ROOT_PASSWORD"],
            "KAFKA_BOOTSTRAP_SERVERS": "kafka:9093",
            "AI_PICKLEBALL_VIDEO_URL": f"http://host.docker.internal:{FAKE_AI_PORT}/api/v1/process",
            "AI_WORKER_SHUTDOWN_GRACE": "5",
        }
        for key in ("KAFKA_TOPIC_GRADING_JOBS", "KAFKA_TOPIC_GRADING_JOBS_SMALL", "KAFKA_TOPIC_GRADING_JOBS_LARGE",
                    "KAFKA_TOPIC_GRADING_RESULTS", "KAFKA_CONSUMER_GROUP_AI"):
            self.env[key] = pipe.env[key]

    def start(self) -> None:
        args = ["run", "-d", "--name", self.name, "--network", NETWORK,
                "--add-host", "host.docker.internal:host-gateway", "--read-only", "--tmpfs", "/tmp",
                "--stop-timeout", "45"]
        for key, value in self.env.items():
            args += ["-e", f"{key}={value}"]
        docker(*args, IMAGE)

    def get(self, path: str) -> tuple[int, dict]:
        code = (
            "import json,urllib.request,urllib.error\n"
            f"try:\n r=urllib.request.urlopen('http://127.0.0.1:8000{path}',timeout=3); print(r.status, r.read().decode())\n"
            "except urllib.error.HTTPError as e: print(e.code, e.read().decode() or '{}')\n"
        )
        out = docker("exec", self.name, "python", "-c", code).strip()
        status, _, body = out.partition(" ")
        return int(status), json.loads(body or "{}")

    def wait_ready(self, timeout: float = 90) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = docker("inspect", "-f", "{{.State.Status}}", self.name, check=False).strip()
            if state == "exited":
                raise RuntimeError("Container worker thoát:\n" + self.logs()[-3000:])
            try:
                status, body = self.get("/health/ready")
                if status == 200 and all(p.get("partitions") for p in body.get("worker_pools", {}).values()):
                    return body
            except (RuntimeError, ValueError):
                pass
            time.sleep(1)
        raise TimeoutError("Container worker không ready:\n" + self.logs()[-3000:])

    def stop(self) -> float:
        started = time.time()
        docker("stop", self.name)
        return time.time() - started

    def logs(self) -> str:
        return docker("logs", self.name, check=False)

    def remove(self) -> None:
        docker("rm", "-f", self.name, check=False)


def run():
    fake_ai = FakeAIProcess(port=FAKE_AI_PORT, host="0.0.0.0").start()
    pipe = Pipeline(fake_ai, APP_ROLE="api")
    workers: list[WorkerContainer] = []
    try:
        pipe.create_topics()
        pipe.start_app()
        _, api_health = pipe.ready()
        assert api_health["role"] == "api" and api_health["worker_pools"] == {}, api_health
        assert api_health["components"]["ai_worker"] == "disabled", api_health

        print("\n[TEST 1] Vai trò của từng process")
        worker = WorkerContainer(pipe, f"test-ai-worker-{pipe.run_id}-1")
        workers.append(worker)
        worker.start()
        health = worker.wait_ready()
        comps = health["components"]
        assert health["role"] == "worker", health
        assert comps["outbox"] == "disabled" and comps["result_consumer"] == "disabled", comps
        assert set(health["worker_pools"]) == {"small", "large"}, health
        status, _ = worker.get("/api/auth/me")
        assert status == 404, status
        print("  ✓ API (APP_ROLE=api): không có worker pool; container (APP_ROLE=worker): chỉ có pool small/large, /api → 404")

        print("\n[TEST 2] Job đi qua API → Kafka → container worker → API")
        ids = [pipe.insert_job("sleep:2") for _ in range(3)]
        docs = pipe.wait_status(ids, timeout=90)
        assert all(d["status"] == "completed" for d in docs.values()), docs
        calls = fake_ai.stats()["calls"]
        assert all(calls.get(str(i)) == 1 for i in ids), calls
        assert "Graded resultId=" in worker.logs() and "Graded resultId=" not in pipe.log()
        print("  ✓ 3 job được container worker chấm (API process không gọi AI), kết quả lưu vào Mongo")

        print("\n[TEST 3] docker stop khi đang có job (grace 5s)")
        short_id = pipe.insert_job("sleep:3")
        long_id = pipe.insert_job("sleep:40")
        pipe.wait_in_flight([short_id, long_id])
        elapsed = worker.stop()
        logs = worker.logs()
        exit_code = docker("inspect", "-f", "{{.State.ExitCode}}", worker.name).strip()
        assert "Traceback" not in logs, logs[-3000:]
        assert "Draining 2 running job(s)" in logs and "Cancelling 1 job(s)" in logs, logs[-3000:]
        assert exit_code == "0", exit_code
        assert elapsed < 20, elapsed
        print(f"  ✓ Container dừng sau {elapsed:.1f}s, exit 0, drain job ngắn, hủy job dài, không traceback")

        worker2 = WorkerContainer(pipe, f"test-ai-worker-{pipe.run_id}-2")
        workers.append(worker2)
        worker2.start()
        worker2.wait_ready()
        docs = pipe.wait_status([short_id, long_id], timeout=120)
        assert all(d["status"] == "completed" for d in docs.values()), docs
        calls = fake_ai.stats()["calls"]
        assert calls[str(short_id)] == 1 and calls[str(long_id)] == 2, calls
        print("  ✓ Container mới nhận lại job dài và chấm xong; job ngắn không bị chấm lại")
        worker2.stop()
        pipe.sigterm()
    finally:
        for w in workers:
            w.remove()
        pipe.cleanup()
        fake_ai.stop()


if __name__ == "__main__":
    run()
    print("\n>>> TEST WORKER CONTAINER PASSED")
