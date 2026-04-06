"""User endpoints: registration, login, profile CRUD."""

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_admin, require_admin_or_self
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.users import Token, UserCreate, UserLogin, UserRead, UserUpdate
from app.services import user_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """Register a new user."""
    return user_service.register_user(db, user_in)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Login with username/email and password. Returns JWT token."""
    user = user_service.authenticate_user(db, credentials.username, credentials.password)
    token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("login success for user_id=%s", user.user_id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> Any:
    """Get current authenticated user."""
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update own profile."""
    return user_service.update_user(db, current_user, user_in)


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    current_user: User = Depends(require_admin_or_self),
    db: Session = Depends(get_db),
) -> Any:
    """Get user by ID. Requires admin or same user."""
    from app.core.exceptions import NotFoundException

    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("User")
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_by_id(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_admin_or_self),
    db: Session = Depends(get_db),
) -> Any:
    """Update a user by ID. Requires admin or same user."""
    user = user_service.update_user_by_id(db, user_id, user_in)
    logger.info("user updated user_id=%s by=%s", user_id, current_user.user_id)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Delete a user by ID. Requires admin."""
    user_service.delete_user(db, user_id)
    logger.info("user deleted user_id=%s by=%s", user_id, current_user.user_id)
    return JSONResponse(
        content={"message": f"User with ID {user_id} deleted successfully."},
        status_code=status.HTTP_200_OK,
    )


@router.get("/by-code/{user_code}", response_model=UserRead)
def get_user_by_code(
    user_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Find a user by their user_code. Requires admin or same user."""
    from sqlmodel import select
    from app.core.exceptions import NotFoundException, PermissionDeniedException
    from app.models.user import UserRole

    user = db.exec(select(User).where(User.user_code == user_code)).first()
    if not user:
        raise NotFoundException("User")

    if current_user.user_role != UserRole.admin and current_user.user_id != user.user_id:
        raise PermissionDeniedException()

    return user


@router.get("/", response_model=list[UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Any:
    """List all users. Requires admin."""
    return user_service.list_users(db, skip=skip, limit=limit)
