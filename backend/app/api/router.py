from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.cameras import router as cameras_router
from app.api.courses import router as courses_router
from app.api.enrollments import router as enrollments_router
from app.api.live_results import router as live_results_router
from app.api.notifications import router as notifications_router
from app.api.sports import router as sports_router
from app.api.student import router as student_router
from app.api.tasks import router as tasks_router
from app.api.teacher import router as teacher_router
from app.api.users import router as users_router
from app.api.video_results import router as video_results_router

api_router = APIRouter(prefix="/api")

# Phân hệ Xác thực & Người dùng
api_router.include_router(auth_router)
api_router.include_router(users_router)

# Phân hệ Giáo viên & Sinh viên
api_router.include_router(teacher_router)
api_router.include_router(student_router)

# Phân hệ Quản lý Đào tạo cốt lõi
api_router.include_router(courses_router)
api_router.include_router(enrollments_router)
api_router.include_router(sports_router)
api_router.include_router(tasks_router)
api_router.include_router(cameras_router)

# Phân hệ Chấm điểm & Kết quả
api_router.include_router(video_results_router)
api_router.include_router(live_results_router)

# Phân hệ Thông báo
api_router.include_router(notifications_router)
