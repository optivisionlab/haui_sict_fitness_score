"""
Fake AI service dùng cho test: HTTP/1.1 keep-alive tối giản, đếm kết nối và request.

Hành vi theo đoạn `fake=<hành vi>` trong `object_key` (vd `submissions/fake=sleep:3/x.mp4`),
hoặc `detail.title` của request kiểu cũ:
- "sleep:<giây>"  -> chờ rồi trả kết quả completed
- "status:<mã>"   -> trả HTTP status tương ứng
- "busy:<n>"      -> n lần gọi đầu của job trả 429 + Retry-After: 1, sau đó completed
- khác            -> trả kết quả completed ngay

`GET /stats` trả số liệu (để test chạy ở process khác đọc được).
Chạy độc lập: python scripts/fake_ai_server.py <port> [host]
"""

import asyncio
import json
import sys
import time


class FakeAIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.connections = 0
        self.requests = 0
        self.concurrent = 0
        self.max_concurrent = 0
        self.job_ids: list[str] = []
        self.calls: dict[str, int] = {}
        self.in_flight: set[str] = set()
        self.done_at: dict[str, float] = {}
        self._server: asyncio.base_events.Server | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/api/v1/process"

    async def start(self) -> "FakeAIServer":
        self._server = await asyncio.start_server(self._handle, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def stats(self) -> dict:
        return {
            "connections": self.connections,
            "requests": self.requests,
            "max_concurrent": self.max_concurrent,
            "calls": self.calls,
            "in_flight": sorted(self.in_flight),
            "done_at": self.done_at,
        }

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connections += 1
        try:
            while True:
                request_line = await reader.readline()
                if not request_line:
                    break
                parts = request_line.decode().split()
                path = parts[1] if len(parts) > 1 else "/"
                length = 0
                while True:
                    line = await reader.readline()
                    if line in (b"\r\n", b"\n", b""):
                        break
                    name, _, value = line.decode().partition(":")
                    if name.strip().lower() == "content-length":
                        length = int(value.strip())
                body = json.loads(await reader.readexactly(length)) if length else {}
                extra = ""
                if path.startswith("/stats"):
                    status, payload = 200, self.stats()
                else:
                    status, payload = await self._process(body)
                    if payload.get("detail") == "Server busy":
                        extra = "Retry-After: 1\r\n"
                data = json.dumps(payload).encode()
                writer.write(
                    f"HTTP/1.1 {status} X\r\nContent-Type: application/json\r\n{extra}"
                    f"Content-Length: {len(data)}\r\nConnection: keep-alive\r\n\r\n".encode() + data
                )
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    async def _process(self, body: dict) -> tuple[int, dict]:
        job_id = body.get("job_id")
        self.requests += 1
        self.job_ids.append(job_id)
        self.calls[job_id] = self.calls.get(job_id, 0) + 1
        self.in_flight.add(job_id)
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            title = (body.get("detail") or {}).get("title", "")
            for part in str(body.get("object_key") or "").split("/"):
                if part.startswith("fake="):
                    title = part[len("fake="):]
            if title.startswith("busy:") and self.calls[job_id] <= int(title.split(":", 1)[1]):
                return 429, {"detail": "Server busy"}
            if title.startswith("status:"):
                return int(title.split(":", 1)[1]), {"detail": "fake error"}
            if title.startswith("sleep:"):
                await asyncio.sleep(float(title.split(":", 1)[1]))
            self.done_at[job_id] = time.time()
            return 200, {
                "job_id": job_id,
                "result_id": body.get("result_id"),
                "status": "completed",
                "score": 8.0,
                "feedback": "fake",
                "metrics": {"accuracy": 0.8, "hitCount": 16, "missCount": 4},
            }
        finally:
            self.concurrent -= 1
            self.in_flight.discard(job_id)


async def _main(port: int, host: str) -> None:
    server = await FakeAIServer(host=host, port=port).start()
    print(f"Fake AI listening on {server.url}", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_main(int(sys.argv[1]) if len(sys.argv) > 1 else 18888, sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"))
