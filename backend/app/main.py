import logging
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.database import init_db, engine
from app.core.database import configure_redis_notifications
import asyncio
from app.core.redis_dispatcher import run_background
from app.api.endpoints import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Background dispatcher handles global Redis -> per-user republish
_redis_dispatcher_task: asyncio.Task | None = None
_redis_dispatcher_stop: asyncio.Event | None = None


# Request logging middleware (logs method, path, status and duration)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000.0
    logger.info(
        "%s %s completed_in=%.2fms status_code=%s",
        request.method,
        request.url.path,
        process_time,
        response.status_code,
    )
    response.headers["X-Process-Time-ms"] = f"{process_time:.2f}"
    return response


# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router directly (fail fast if there is an import error)
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def on_startup():
    # create DB tables if necessary
    try:
        init_db()
    except Exception:
        # don't crash startup on DB init problems here; surface later on real requests
        logger.exception("Database initialization failed at startup")

    # Ensure Redis will emit keyspace/keyevent notifications required by our SSE
    try:
        configure_redis_notifications()
    except Exception:
        logger.exception("Failed to configure Redis keyspace notifications during startup")

    # Start global Redis dispatcher as a background task. It listens for keyevents
    # and republishes messages to per-user channels so SSE clients can subscribe
    # to a small, dedicated channel.
    try:
        global _redis_dispatcher_task, _redis_dispatcher_stop
        if _redis_dispatcher_task is None:
            _redis_dispatcher_stop = asyncio.Event()
            _redis_dispatcher_task = asyncio.create_task(run_background(_redis_dispatcher_stop))
            logger.info("Started redis_dispatcher background task")
    except Exception:
        logger.exception("Failed to start redis dispatcher")

    # Log all registered routes for visibility
    try:
        routes = [
            f"{','.join(sorted(getattr(r, 'methods', []) or []))} {getattr(r, 'path', '')}"
            for r in app.routes
        ]
        logger.info("Registered routes (%d):\n%s", len(routes), "\n".join(routes))
    except Exception:
        logger.debug("Failed to list routes on startup", exc_info=True)


@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check that verifies DB connectivity."""
    try:
        with engine.connect() as conn:
            # lightweight check
            conn.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Service unavailable")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        routes=app.routes,
    )
    # Add Bearer auth scheme for JWT tokens
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    # Set global security requirement so docs use Bearer token input
    openapi_schema.setdefault("security", [])
    openapi_schema["security"].append({"bearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def read_root():
    return {"status": "ok", "project": settings.PROJECT_NAME}


@app.on_event("shutdown")
async def on_shutdown():
    """Stop the redis dispatcher background task cleanly."""
    global _redis_dispatcher_task, _redis_dispatcher_stop
    try:
        if _redis_dispatcher_stop is not None:
            _redis_dispatcher_stop.set()
        if _redis_dispatcher_task is not None:
            # give it a short timeout to exit
            await asyncio.wait_for(_redis_dispatcher_task, timeout=3.0)
    except asyncio.TimeoutError:
        try:
            _redis_dispatcher_task.cancel()
        except Exception:
            pass
    except Exception:
        logger.exception("Error while shutting down redis dispatcher")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)