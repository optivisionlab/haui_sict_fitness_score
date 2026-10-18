import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Đăng ký các bộ xử lý lỗi toàn cục để chuẩn hóa định dạng lỗi đầu ra."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Lỗi xử lý yêu cầu"
        data = None if isinstance(detail, str) else detail

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": exc.status_code,
                "message": message,
                "data": data,
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()

        # Tạo thông báo lỗi ngắn gọn, thân thiện
        formatted_messages = []
        for err in errors:
            loc = " -> ".join(str(item) for item in err.get("loc", []) if item != "body")
            msg = err.get("msg", "Giá trị không hợp lệ")
            formatted_messages.append(f"[{loc}]: {msg}" if loc else msg)

        summary_msg = "; ".join(formatted_messages) if formatted_messages else "Dữ liệu đầu vào không hợp lệ"

        # Chuẩn hóa chi tiết lỗi (chuyển đổi types không serialize được nếu có)
        clean_errors = []
        for err in errors:
            clean_err = dict(err)
            clean_err["loc"] = [str(item) for item in clean_err.get("loc", [])]
            if "ctx" in clean_err:
                clean_err["ctx"] = {k: str(v) for k, v in clean_err["ctx"].items()}
            clean_errors.append(clean_err)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": f"Dữ liệu không hợp lệ: {summary_msg}",
                "data": clean_errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception at %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Đã xảy ra lỗi máy chủ nội bộ. Vui lòng liên hệ quản trị viên.",
                "data": None,
            },
        )
