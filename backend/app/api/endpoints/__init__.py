from fastapi import APIRouter
from app.api.endpoints import users, classes, exams, redis_events, results, demo_api 

api_router = APIRouter()

# Sử dụng plural và gợi nhớ REST
api_router.include_router(users.router, prefix="/user", tags=["Users"])
api_router.include_router(classes.router, prefix="/class", tags=["Classes"])
api_router.include_router(exams.router, prefix="/exam", tags=["Exams"])
api_router.include_router(redis_events.router, prefix="/redis", tags=["Redis"])
api_router.include_router(results.router, prefix="/result", tags=["Results"])
api_router.include_router(demo_api.router, prefix="/demo",tags=["Demo"])