from fastapi import APIRouter

from app.api.endpoints import classes, demo_api, exams, redis_events, results, users

api_router = APIRouter()

api_router.include_router(users.router, prefix="/user", tags=["Users"])
api_router.include_router(classes.router, prefix="/class", tags=["Classes"])
api_router.include_router(exams.router, prefix="/exam", tags=["Exams"])
api_router.include_router(redis_events.router, prefix="/redis", tags=["Redis"])
api_router.include_router(results.router, prefix="/result", tags=["Results"])
api_router.include_router(demo_api.router, prefix="/demo", tags=["Demo"])
