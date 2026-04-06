"""FastAPI application entry point with lifespan management."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from app.api.endpoints import api_router
from app.core.config import settings
from app.core.database import engine, init_db
from app.core.exceptions import register_exception_handlers
from app.core.redis import configure_redis_notifications
from app.core.redis_dispatcher import run_background

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # --- Startup ---
    try:
        init_db()
    except Exception:
        logger.exception("Database initialization failed at startup")

    try:
        configure_redis_notifications()
    except Exception:
        logger.exception("Failed to configure Redis keyspace notifications")

    stop_event = asyncio.Event()
    dispatcher_task = asyncio.create_task(run_background(stop_event))
    logger.info("Started redis_dispatcher background task")

    # Log registered routes
    try:
        routes = [
            f"{','.join(sorted(getattr(r, 'methods', []) or []))} {getattr(r, 'path', '')}"
            for r in app.routes
        ]
        logger.info("Registered routes (%d):\n%s", len(routes), "\n".join(routes))
    except Exception:
        logger.debug("Failed to list routes", exc_info=True)

    yield

    # --- Shutdown ---
    stop_event.set()
    try:
        await asyncio.wait_for(dispatcher_task, timeout=3.0)
    except asyncio.TimeoutError:
        dispatcher_task.cancel()
    except Exception:
        logger.exception("Error shutting down redis dispatcher")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json" if not settings.API_V1_STR else f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

register_exception_handlers(app)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000.0
    logger.info(
        "%s %s completed_in=%.2fms status_code=%s",
        request.method,
        request.url.path,
        duration_ms,
        response.status_code,
    )
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.2f}"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    """Verify DB connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("Health check failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/")
def read_root():
    return {"status": "ok", "project": settings.PROJECT_NAME}


# ---------------------------------------------------------------------------
# Custom OpenAPI schema
# ---------------------------------------------------------------------------

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    openapi_schema.setdefault("security", [])
    openapi_schema["security"].append({"bearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=2305, reload=True)
