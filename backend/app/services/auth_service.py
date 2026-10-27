from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.crud.user import crud_user
from app.models.user import User, UserRole
from app.schemas.user import TokenData

# Argon2id theo khuyến nghị OWASP (m=19 MiB, t=2, p=1). Mặc định của argon2-cffi (m=64 MiB, p=4)
# làm ~40 lượt đăng nhập đồng thời chiếm >2,5 GB RAM và container backend (768 MB) bị OOM-kill.
ph = PasswordHasher(
    time_cost=settings.PASSWORD_HASH_TIME_COST,
    memory_cost=settings.PASSWORD_HASH_MEMORY_KIB,
    parallelism=settings.PASSWORD_HASH_PARALLELISM,
)
# Băm/kiểm tra mật khẩu chạy trên một thread pool riêng, cố định PASSWORD_HASH_CONCURRENCY luồng:
# - RAM đỉnh = số luồng x memory_cost, các lượt còn lại xếp hàng (chậm hơn chút thay vì sập);
# - glibc giữ lại bộ đệm Argon2 (vài chục MB) trong arena của từng luồng đã băm: nếu băm trên
#   threadpool ~40 luồng của FastAPI, mỗi worker giữ tới hàng trăm MB. Pool cố định giới hạn việc đó.
_password_pool = ThreadPoolExecutor(
    max_workers=settings.PASSWORD_HASH_CONCURRENCY, thread_name_prefix="password-hash"
)


def _in_password_pool(fn, *args):
    return _password_pool.submit(fn, *args).result()


security = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(password: str) -> str:
    """Hash mật khẩu bằng Argon2."""
    return _in_password_pool(ph.hash, password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu hỗ trợ cả Argon2 và Bcrypt."""
    if hashed_password.startswith("$argon2"):
        try:
            return _in_password_pool(ph.verify, hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    elif hashed_password.startswith("$2"):
        try:
            return _in_password_pool(
                bcrypt.checkpw, plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    # Không cho phép mật khẩu dạng plain text để đảm bảo bảo mật
    return False


def password_needs_rehash(hashed_password: str) -> bool:
    """True nếu hash dùng thuật toán/tham số cũ (bcrypt, Argon2 mặc định cũ) cần băm lại."""
    if not hashed_password.startswith("$argon2"):
        return True
    try:
        return ph.check_needs_rehash(hashed_password)
    except Exception:
        return False


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Tạo JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Giải mã và kiểm tra JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Dependency lấy thông tin user hiện tại từ Bearer Token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub") or payload.get("user_id")
    if not user_id:
        raise credentials_exception

    user = await crud_user.aget(user_id)
    if not user:
        raise credentials_exception

    if user.user_status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị khóa",
        )

    return user


def require_roles(*roles: UserRole):
    """Dependency kiểm tra quyền truy cập theo vai trò (Role-based access control)."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện hành động này",
            )
        return current_user

    return role_checker


async def verify_course_teacher(
    course_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """
    Object-Level RBAC Guard: Kiểm tra giáo viên chỉ được phép can thiệp vào lớp học mình phụ trách.
    Admin có quyền can thiệp vào tất cả các lớp.
    """
    from app.crud.course import crud_course

    course = await crud_course.aget(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy lớp học phần với ID: {course_id}",
        )

    if current_user.role != UserRole.ADMIN and str(course.teacher_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản lý lớp học phần này",
        )

    return course


async def verify_student_in_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Object-Level RBAC Guard: Kiểm tra sinh viên có thực sự đang ghi danh active trong lớp hay không.
    """
    from app.crud.enrollment import crud_enrollment

    enrollment = await crud_enrollment.aget_by_user_and_course(
        user_id=str(current_user.id),
        course_id=course_id,
    )
    if not enrollment or enrollment.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chưa ghi danh hoặc không có quyền truy cập vào lớp học này",
        )

    return enrollment


async def verify_internal_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> bool:
    """
    Xác thực cho AI worker / camera streaming service hoặc admin/teacher.
    Chấp nhận:
    1. Header X-API-Key: AI_API_KEY
    2. Bearer Token của người dùng có quyền (ADMIN, TEACHER)
    """
    if api_key and api_key == settings.AI_API_KEY:
        return True

    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = await crud_user.aget(user_id)
                if user and user.role in (UserRole.ADMIN, UserRole.TEACHER):
                    return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Yêu cầu API Key hợp lệ hoặc quyền Admin/Teacher",
    )

