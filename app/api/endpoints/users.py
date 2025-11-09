from datetime import timedelta
from typing import Any, List
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from sqlmodel import Session, select
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserStatus, UserRole
from app.schemas.users import UserCreate, UserUpdate, Token, UserRead, UserLogin

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Create new user.
    """
    # Basic validation
    if not user_in.password:
        raise HTTPException(status_code=400, detail="Password is required")

    # Normalize inputs
    email = user_in.email.strip() if user_in.email else None
    user_name = user_in.user_name.strip() if user_in.user_name else None

    # Check if user with same email exists
    user = db.exec(select(User).where(User.email == email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists."
        )
    
    # Check if user with same username exists
    user = db.exec(select(User).where(User.user_name == user_name)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists."
        )
    
    # Dùng hash_password (có SHA-256 trước bcrypt)
    # Create user with hashed password (do not mutate incoming Pydantic model)
    payload = user_in.dict(exclude={"password"})
    if email is not None:
        payload["email"] = email
    if user_name is not None:
        payload["user_name"] = user_name

    user = User(
        **payload,
        password=hash_password(user_in.password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Login with JSON body {username, password}."""
    username = credentials.username
    password = credentials.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = db.exec(
        select(User).where(
            (User.email == username) | (User.user_name == username)
        )
    ).first()

    if not user or not verify_password(password, user.password):
        logger.info("login failed for username=%s", username)
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")

    if user.user_status != UserStatus.active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = {
        "access_token": create_access_token(
            data={"sub": str(user.user_id)},
            expires_delta=access_token_expires,
        ),
        "token_type": "bearer",
    }
    logger.info("login success for user_id=%s", getattr(user, "user_id", None))
    return token


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user.
    """
    # Log safe subset of current_user (avoid sensitive fields)
    try:
        logger.info(
            "[users.me] user_id=%s user_name=%s email=%s role=%s status=%s",
            getattr(current_user, "user_id", None),
            getattr(current_user, "user_name", None),
            getattr(current_user, "email", None),
            getattr(current_user, "user_role", None),
            getattr(current_user, "user_status", None),
        )
    except Exception:
        print({
            "endpoint": "/api/v1/user/me",
            "user_id": getattr(current_user, "user_id", None),
            "user_name": getattr(current_user, "user_name", None),
            "email": getattr(current_user, "email", None),
            "user_role": getattr(current_user, "user_role", None),
            "user_status": getattr(current_user, "user_status", None),
        })
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update own user.
    """
    # Use a mutable dict to avoid mutating the Pydantic model
    update_data = user_in.dict(exclude_unset=True)
    if "password" in update_data and update_data.get("password"):
        update_data["password"] = hash_password(update_data["password"])

    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get user by ID.
    """
    # Allow access if the requester is admin or requesting their own record
    if not (current_user.user_role == UserRole.admin or current_user.user_id == user_id):
        raise HTTPException(
            status_code=403,
            detail="Not enough permissions"
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_by_id(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Update a user's information by user_id. Allowed for admin or the user themself.
    Performs uniqueness checks for email and username and hashes password when provided.
    """
    # Permission check
    if not (current_user.user_role == UserRole.admin or current_user.user_id == user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Uniqueness checks
    update_data = user_in.dict(exclude_unset=True)
    if "email" in update_data and update_data["email"]:
        existing = db.exec(select(User).where(User.email == update_data["email"], User.user_id != user_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
    if "user_name" in update_data and update_data["user_name"]:
        existing = db.exec(select(User).where(User.user_name == update_data["user_name"], User.user_id != user_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already in use")

    # Hash password if present
    if "password" in update_data and update_data.get("password"):
        update_data["password"] = hash_password(update_data["password"])

    for field, value in update_data.items():
        setattr(user, field, value)
    logger.info("user updated user_id=%s by=%s", user.user_id, getattr(current_user, "user_id", None))

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Delete a user by ID. Allowed for admin or the user themself.
    """
    # Permission check
    if not (current_user.user_role == UserRole.admin or current_user.user_id == user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    logger.info("user deleted user_id=%s by=%s", user.user_id, getattr(current_user, "user_id", None))
    # Return an empty Response for 204 to avoid sending a response body
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/by-code/{user_code}", response_model=UserRead)
def get_user_by_code(
    user_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Find a user by their user_code. Accessible to admins or the user themself.
    """
    user = db.exec(select(User).where(User.user_code == user_code)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Allow if admin or owner
    if not (current_user.user_role == UserRole.admin or current_user.user_id == user.user_id):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return user


@router.get("/", response_model=List[UserRead])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve users.
    """
    # Only admins can list all users
    if current_user.user_role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    users = db.exec(select(User).offset(skip).limit(limit)).all()
    return users