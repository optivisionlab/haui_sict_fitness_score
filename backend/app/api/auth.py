from fastapi import APIRouter, Depends, status

from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services.auth_service import get_current_user
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate):
    """Đăng ký tài khoản người dùng mới."""
    user = user_service.register(user_in)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
def login(login_data: UserLogin):
    """Đăng nhập và nhận JWT access token."""
    _, token = user_service.login(login_data)
    return token


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin tài khoản hiện tại từ JWT token."""
    return UserRead.model_validate(current_user)
