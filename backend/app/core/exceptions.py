"""Custom exceptions and global exception handlers for the application."""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource", detail: str | None = None):
        super().__init__(404, detail or f"{resource} not found")


class AlreadyExistsException(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(400, detail)


class PermissionDeniedException(AppException):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(403, detail)


class InvalidInputException(AppException):
    def __init__(self, detail: str = "Invalid input"):
        super().__init__(400, detail)


class ExternalServiceException(AppException):
    def __init__(self, detail: str = "External service error"):
        super().__init__(502, detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
