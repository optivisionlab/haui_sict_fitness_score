import logging
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.core.database import init_db, engine
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
def on_startup():
    # create DB tables if necessary
    try:
        init_db()
    except Exception:
        # don't crash startup on DB init problems here; surface later on real requests
        logger.exception("Database initialization failed at startup")

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