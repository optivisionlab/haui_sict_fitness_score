import json
import logging
from typing import Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    """Middleware tự động bọc dữ liệu trả về từ các endpoint /api thành định dạng chuẩn."""

    async def dispatch(self, request: Request, call_next):
        # Bỏ qua các đường dẫn tài liệu Swagger/Redoc, OpenAPI và health check
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        response = await call_next(request)

        # Chỉ can thiệp vào các response dạng JSON
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Đọc nội dung body
        body_chunks = [chunk async for chunk in response.body_iterator]
        body_bytes = b"".join(body_chunks)

        try:
            raw_text = body_bytes.decode("utf-8")
            if not raw_text.strip():
                data = None
            else:
                data = json.loads(raw_text)

            # Nếu dữ liệu đã được bọc chuẩn (ví dụ từ exception handler hoặc custom response), giữ nguyên
            if isinstance(data, dict) and "success" in data and "code" in data and "data" in data:
                new_bytes = body_bytes
            else:
                status_code = response.status_code
                is_success = status_code < 400

                # Xử lý trường hợp MessageResponse thuần
                msg = "Thành công" if is_success else "Lỗi xử lý"
                res_data: Any = data

                if isinstance(data, dict) and "message" in data and len(data) <= 2:
                    msg = data["message"]
                    res_data = data.get("detail", None)

                wrapped = {
                    "success": is_success,
                    "code": status_code,
                    "message": msg,
                    "data": res_data,
                }
                new_bytes = json.dumps(wrapped, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            logger.debug("Không thể bọc response JSON: %s", e)
            new_bytes = body_bytes

        # Cập nhật Content-Length header
        new_headers = dict(response.headers)
        new_headers["content-length"] = str(len(new_bytes))

        return Response(
            content=new_bytes,
            status_code=response.status_code,
            headers=new_headers,
            media_type="application/json",
        )


def setup_cors(app: FastAPI) -> None:
    """Cấu hình CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )


def setup_middlewares(app: FastAPI) -> None:
    """Đăng ký tất cả middlewares cho ứng dụng."""
    # Thứ tự: CORS -> ResponseWrapper
    app.add_middleware(ResponseWrapperMiddleware)
    setup_cors(app)
