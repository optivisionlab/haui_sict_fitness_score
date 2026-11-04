"""Test 1 bài nộp đi hết luồng như trình duyệt và đo thời gian từng bước.

UI -> POST /upload-url -> PUT presigned (MinIO) -> POST /confirm-upload
   -> outbox -> Kafka -> ai-worker -> AI service -> Kafka results -> backend -> GET /status

Ví dụ (đo nội bộ, không qua Cloudflare):
    python3 scripts/bench_e2e_flow.py video.mp4 --task <task_id> --course <course_id> --duration 3 \
        --base http://127.0.0.1:4200 --minio-direct 100.116.40.89:9000
In ra JSON: thời gian từng bước (upload-url, PUT MinIO, confirm, pending -> completed) và điểm.
Bài nộp tạo ra là thật: dùng bài tập/tài khoản test rồi xoá sau khi đo.
"""
import argparse
import json
import mimetypes
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime

p = argparse.ArgumentParser()
p.add_argument("video")
p.add_argument("--base", default="http://127.0.0.1:4200", help="frontend nginx (proxy /api)")
p.add_argument("--email", default="ducpm@sv.haui.edu.vn")
p.add_argument("--password", default="123456")
p.add_argument("--task", required=True)
p.add_argument("--course", default=None)
p.add_argument("--duration", type=int, default=None, help="duration_sec gửi lên (frontend hiện không gửi)")
p.add_argument("--poll", type=float, default=1.0)
p.add_argument("--minio-direct", default=None, help="vd 100.116.40.89:9000: PUT thẳng MinIO máy này")
args = p.parse_args()

UA = {"User-Agent": "fitness-e2e-bench/1.0"}


def call(method, url, body=None, token=None, headers=None, raw=None):
    h = dict(UA)
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            txt = r.read()
            return r.status, (json.loads(txt) if txt and txt[:1] in b"{[" else txt)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url} -> {e.code} {e.read()[:400]!r}")


def data(resp):
    return resp.get("data", resp) if isinstance(resp, dict) else resp


marks = {}
t0 = time.time()


def mark(name):
    marks[name] = time.time()


api = args.base.rstrip("/") + "/api"
_, r = call("POST", f"{api}/auth/login", {"email": args.email, "password": args.password})
tok = data(r).get("accessToken") or data(r).get("access_token")
mark("login")

size = os.path.getsize(args.video)
ctype = mimetypes.guess_type(args.video)[0] or "video/mp4"
body = {"task_id": args.task, "course_id": args.course, "file_name": os.path.basename(args.video),
        "content_type": ctype, "file_size": size}
if args.duration is not None:
    body["duration_sec"] = args.duration
_, r = call("POST", f"{api}/video-results/upload-url", body, tok)
up = data(r)
upload_url = up.get("uploadUrl") or up.get("upload_url")
upload_id = up.get("uploadId") or up.get("upload_id")
result_id = up.get("resultId") or up.get("result_id")
mark("upload_url")

with open(args.video, "rb") as f:
    payload = f.read()
put_headers = {"Content-Type": ctype}
if args.minio_direct:
    # Gửi thẳng tới MinIO máy này, giữ Host gốc để chữ ký presigned (SigV4 ký header host) còn hợp lệ
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(upload_url)
    put_headers["Host"] = parts.netloc
    upload_url = urlunsplit(("http", args.minio_direct, parts.path, parts.query, ""))
call("PUT", upload_url, raw=payload, headers=put_headers)
mark("put_minio")

_, r = call("POST", f"{api}/video-results/confirm-upload", {"upload_id": upload_id}, tok)
mark("confirm")

status = None
while True:
    _, r = call("GET", f"{api}/video-results/{result_id}/status", token=tok)
    st = data(r)
    if st.get("status") != status:
        status = st.get("status")
        mark(f"status:{status}")
    if status in ("completed", "failed"):
        break
    if time.time() - t0 > 3600:
        raise SystemExit("timeout")
    time.sleep(args.poll)

prev = t0
steps = []
for k, v in marks.items():
    steps.append((k, round(v - prev, 3), round(v - t0, 3)))
    prev = v
out = {"resultId": result_id, "video": os.path.basename(args.video), "sizeMB": round(size / 2**20, 2),
       "t0": datetime.fromtimestamp(t0).isoformat(), "steps": steps, "final": st,
       "upload_MBps": round(size / 2**20 / (marks["put_minio"] - marks["upload_url"]), 2)}
print(json.dumps(out, ensure_ascii=False))
