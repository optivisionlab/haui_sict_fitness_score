"""
Fake AI service dùng cho test: HTTP/1.1 keep-alive tối giản, đếm số kết nối TCP.

Hành vi theo `detail.title` của request:
- "sleep:<giây>"  -> chờ rồi trả kết quả completed
- "status:<mã>"   -> trả HTTP status tương ứng
- khác            -> trả kết quả completed ngay
"""

import asyncio
import json


class FakeAIServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.connections = 0
        self.requests = 0
        self.concurrent = 0
        self.max_concurrent = 0
        self.job_ids: list[str] = []
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

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connections += 1
        try:
            while True:
                request_line = await reader.readline()
                if not request_line:
                    break
                length = 0
                while True:
                    line = await reader.readline()
                    if line in (b"\r\n", b"\n", b""):
                        break
                    name, _, value = line.decode().partition(":")
                    if name.strip().lower() == "content-length":
                        length = int(value.strip())
                body = json.loads(await reader.readexactly(length)) if length else {}
                status, payload = await self._process(body)
                data = json.dumps(payload).encode()
                writer.write(
                    f"HTTP/1.1 {status} X\r\nContent-Type: application/json\r\n"
                    f"Content-Length: {len(data)}\r\nConnection: keep-alive\r\n\r\n".encode() + data
                )
                await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    async def _process(self, body: dict) -> tuple[int, dict]:
        self.requests += 1
        self.job_ids.append(body.get("job_id"))
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            title = (body.get("detail") or {}).get("title", "")
            if title.startswith("status:"):
                return int(title.split(":", 1)[1]), {"detail": "fake error"}
            if title.startswith("sleep:"):
                await asyncio.sleep(float(title.split(":", 1)[1]))
            return 200, {
                "job_id": body.get("job_id"),
                "result_id": body.get("result_id"),
                "status": "completed",
                "score": 8.0,
                "feedback": "fake",
                "metrics": {"accuracy": 0.8, "hitCount": 16, "missCount": 4},
            }
        finally:
            self.concurrent -= 1
