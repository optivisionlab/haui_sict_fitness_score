from fastapi import APIRouter
from app.api.endpoints import users, classes, exams

api_router = APIRouter()

# Sử dụng plural và gợi nhớ REST
api_router.include_router(users.router, prefix="/user", tags=["Users"])
api_router.include_router(classes.router, prefix="/class", tags=["Classes"])
api_router.include_router(exams.router, prefix="/exam", tags=["Exams"])
