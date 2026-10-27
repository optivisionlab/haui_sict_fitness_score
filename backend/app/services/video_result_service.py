import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, UploadFile, status
from pymongo.errors import DuplicateKeyError
from pymongo.results import InsertOneResult
from app.crud.base import to_object_id
from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.sport import crud_sport
from app.crud.task import crud_task
from app.crud.user import crud_user
from app.crud.video_result import crud_video_result
from app.core.config import settings
from app.core.database import get_db
from app.models.course import Course
from app.models.notification import NotificationType
from app.models.sport import SportMode
from app.models.task import GradingMethod, Task, TaskCategory
from app.models.user import UserRole
from app.models.video_result import VideoResult
from app.schemas.video_result import (
    SubmissionItemResponse,
    VideoResultAIUpdate,
    VideoResultCreate,
    VideoResultStatusResponse,
    VideoResultTeacherGrade,
    VideoUploadUrlRequest,
    VideoUploadUrlResponse,
)
from app.services.enrollment_service import enrollment_service
from app.services.grading_job import build_grading_job
from app.services.minio_service import minio_service
from app.services.notification_service import notification_service
from app.services.sports.registry import sport_registry

# AI service (pickleball_track) chỉ đọc được MP4/MOV
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB
UPLOAD_URL_TTL_SECONDS = 600
LEGACY_UPLOAD_TOO_LARGE_MESSAGE = (
    f"Video quá lớn cho POST /video-results/upload (tối đa {settings.LEGACY_UPLOAD_MAX_BYTES // (1024 * 1024)}MB). "
    "Hãy dùng upload-url + confirm-upload để tải video lớn."
)

logger = logging.getLogger(__name__)

# Số lần thử lấy attemptNo mới khi nhiều bài nộp đồng thời
ATTEMPT_INSERT_RETRIES = 5


class VideoResultService:
    @staticmethod
    def _next_attempt_no(task_id: str, user_id: str) -> int:
        latest = crud_video_result.collection.find_one(
            {"taskId": str(task_id), "userId": str(user_id)},
            {"attemptNo": 1},
            sort=[("attemptNo", -1)],
        )
        return (latest["attemptNo"] if latest else 0) + 1

    def _insert_with_free_attempt(self, data: dict, insert):
        """Ghi bài nộp; trùng attemptNo (SV nộp nhiều bài cùng lúc) thì lấy số lần nộp kế tiếp.

        attemptNo được tính trước khi ghi nên 2 request đồng thời có thể ra cùng số; index unique
        (taskId, userId, attemptNo) chặn bản thứ hai, ta lấy số mới thay vì trả lỗi 500.
        Trùng khóa khác (vd _id khi confirm lại) được ném lại cho caller xử lý.
        """
        for _ in range(ATTEMPT_INSERT_RETRIES):
            try:
                created = insert(data)
                return created if not isinstance(created, InsertOneResult) else data
            except DuplicateKeyError as exc:
                if "attemptNo" not in ((exc.details or {}).get("keyPattern") or {}):
                    raise
                data["attemptNo"] = self._next_attempt_no(data["taskId"], data["userId"])
                if isinstance(data.get("gradingJob"), dict):
                    data["gradingJob"]["attemptNo"] = data["attemptNo"]
                logger.info("attemptNo clash for task=%s user=%s, retrying with %s",
                            data["taskId"], data["userId"], data["attemptNo"])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Có nhiều bài nộp cùng lúc cho bài tập này, vui lòng thử lại",
        )

    def _validate_submission_guards(
        self, task_id: str, user_id: str, sport_id: str
    ) -> tuple[Task, Course, int]:
        """
        3 Lớp Bảo Vệ (3-Layer Guards):
        1. Kiểm tra lớp đã chốt sổ điểm chưa.
        2. Kiểm tra cờ khóa nộp bài cấp lớp (allowPracticeSubmission / allowExamSubmission).
        3. Kiểm tra bài tập có bị khóa hoặc ngoài khung giờ nộp bài.
        """
        task = crud_task.get(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bài tập ID {task_id}",
            )

        course = crud_course.get(task.course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy khóa học chứa bài tập này",
            )

        if str(task.sport_id) != str(sport_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Môn thể thao của bài tập không khớp với môn trong yêu cầu",
            )

        enrollment = crud_enrollment.get_by_user_and_course(user_id, task.course_id)
        if not enrollment or enrollment.status.value != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn chưa ghi danh hoặc không còn quyền học khóa học này",
            )

        # GUARD 1: Kiểm tra trạng thái chốt điểm của lớp học phần
        if course.is_grade_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lớp học phần đã chốt sổ điểm, không thể nộp thêm bài",
            )

        # GUARD 2: Kiểm tra cờ khóa nộp bài cấp lớp học phần
        task_category = getattr(task, "category", TaskCategory.PRACTICE)
        if task_category == TaskCategory.PRACTICE and not course.allow_practice_submission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Giảng viên đã khóa nộp bài luyện tập cho lớp học này",
            )
        if task_category == TaskCategory.EXAM and not course.allow_exam_submission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Giảng viên đã khóa nộp bài kiểm tra/thi cho lớp học này",
            )

        # GUARD 3: Kiểm tra bài tập có bị khóa hoặc ngoài khung giờ nộp bài
        now = datetime.now(timezone.utc)
        if getattr(task, "is_locked", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bài tập này hiện đang bị khóa nộp bài",
            )
        if task.close_time:
            close_time = task.close_time if task.close_time.tzinfo else task.close_time.replace(tzinfo=timezone.utc)
            if now > close_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bài tập đã hết hạn nộp bài",
                )
        if task.open_time:
            open_time = task.open_time if task.open_time.tzinfo else task.open_time.replace(tzinfo=timezone.utc)
            if now < open_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bài tập chưa tới thời gian mở nộp bài",
                )

        existing_count = crud_video_result.collection.count_documents({
            "taskId": str(task_id),
            "userId": str(user_id),
        })
        active_uploads = get_db().video_upload_sessions.count_documents({
            "taskId": str(task_id),
            "userId": str(user_id),
            "status": "uploading",
            "expiresAt": {"$gt": datetime.now(timezone.utc)},
        })
        # Không giới hạn số lần nộp: mọi bài tập, bài kiểm tra và bài thi đều được nộp lại
        # (task.maxAttempts không còn được áp dụng).

        # Kiểm tra sport
        sport = crud_sport.get(sport_id)
        if not sport:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy môn thể thao ID {sport_id}",
            )

        if sport.mode != SportMode.VIDEO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Môn thể thao này không áp dụng hình thức nộp video",
            )

        max_attempt_doc = crud_video_result.collection.find_one(
            {"taskId": str(task_id), "userId": str(user_id)},
            {"attemptNo": 1},
            sort=[("attemptNo", -1)],
        )
        max_existing = max_attempt_doc["attemptNo"] if max_attempt_doc else 0
        next_attempt = max(existing_count + active_uploads, max_existing) + 1
        return task, course, next_attempt

    def _resolve_task_id(self, task_id: str, course_id: Optional[str]) -> str:
        if ObjectId.is_valid(task_id):
            task = crud_task.get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")
            if course_id and str(task.course_id) != str(course_id):
                raise HTTPException(status_code=400, detail="Bài tập không thuộc khóa học đã chọn")
            return str(task.id)

        if not course_id:
            raise HTTPException(status_code=400, detail="course_id bắt buộc khi task_id là alias")

        tasks = list(get_db().tasks.find({"courseId": str(course_id)}).sort("createdAt", 1))
        if not tasks:
            raise HTTPException(status_code=404, detail="Khóa học chưa có bài tập")

        alias = task_id.lower()
        if "tx1" in alias or alias == "task-0":
            index = 0
        elif "tx2" in alias or alias == "task-1":
            index = min(1, len(tasks) - 1)
        elif "midterm" in alias or alias == "task-2":
            index = min(2, len(tasks) - 1)
        elif "final" in alias:
            index = len(tasks) - 1
        else:
            raise HTTPException(status_code=404, detail="Không xác định được bài tập từ alias")
        return str(tasks[index]["_id"])

    def create_upload_url(self, user_id: str, upload_in: VideoUploadUrlRequest) -> VideoUploadUrlResponse:
        filename = Path(upload_in.file_name).name
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Định dạng video không được hỗ trợ")
        if upload_in.file_size > MAX_VIDEO_SIZE:
            raise HTTPException(status_code=400, detail="Dung lượng video vượt quá giới hạn 500MB")
        if not upload_in.content_type.lower().startswith("video/") and upload_in.content_type.lower() != "application/octet-stream":
            raise HTTPException(status_code=400, detail="Content-Type không phải định dạng video")

        task_id = self._resolve_task_id(upload_in.task_id, upload_in.course_id)
        task = crud_task.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")
        if task.time_limit and upload_in.duration_sec and upload_in.duration_sec > task.time_limit:
            raise HTTPException(
                status_code=400,
                detail=f"Video dài {upload_in.duration_sec}s, vượt thời lượng tối đa của bài tập ({task.time_limit}s)",
            )
        _, _, attempt_no = self._validate_submission_guards(task_id, user_id, task.sport_id)
        sport = crud_sport.get(task.sport_id)
        if not sport:
            raise HTTPException(status_code=404, detail="Không tìm thấy môn thể thao")

        now = datetime.now(timezone.utc)
        upload_id = ObjectId()
        result_id = ObjectId()
        object_key = f"submissions/{task_id}/{result_id}{extension}"
        expires_at = now + timedelta(seconds=UPLOAD_URL_TTL_SECONDS)
        session = {
            "_id": upload_id,
            "resultId": result_id,
            "taskId": task_id,
            "courseId": str(task.course_id),
            "sportId": str(task.sport_id),
            "sportCode": sport.code.upper(),
            "sportMode": sport.mode.value.upper(),
            "userId": str(user_id),
            "attemptNo": attempt_no,
            "bucket": minio_service.default_bucket,
            "objectKey": object_key,
            "fileName": filename,
            "contentType": upload_in.content_type,
            "declaredFileSize": upload_in.file_size,
            "durationSec": upload_in.duration_sec,
            "taskDetail": {
                "title": task.title,
                "category": task.category.value,
                "gradingMethod": task.grading_method.value,
                "timeLimit": task.time_limit,
            },
            "status": "uploading",
            "expiresAt": expires_at,
            "createdAt": now,
        }
        get_db().video_upload_sessions.insert_one(session)
        upload_url = minio_service.get_presigned_put_url(
            object_name=object_key,
            expires=timedelta(seconds=UPLOAD_URL_TTL_SECONDS),
        )
        return VideoUploadUrlResponse(
            upload_id=str(upload_id),
            result_id=str(result_id),
            object_key=object_key,
            upload_url=upload_url,
            expires_in=UPLOAD_URL_TTL_SECONDS,
        )

    def confirm_upload(self, user_id: str, upload_id: str) -> VideoResult:
        upload_oid = to_object_id(upload_id)
        if not upload_oid:
            raise HTTPException(status_code=400, detail="upload_id không hợp lệ")
        sessions = get_db().video_upload_sessions
        session = sessions.find_one({"_id": upload_oid, "userId": str(user_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên upload")

        result_id = session["resultId"]
        existing = crud_video_result.collection.find_one({"_id": result_id})
        if existing:
            return VideoResult.model_validate(existing)
        expires_at = session["expiresAt"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if session.get("status") != "uploading" or expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Phiên upload đã hết hạn hoặc không còn hiệu lực")

        try:
            object_stat = minio_service.stat_object(session["objectKey"], session["bucket"])
        except Exception as exc:
            logger.warning("MinIO object verification failed for uploadId=%s: %s", upload_id, exc)
            raise HTTPException(status_code=400, detail="Không tìm thấy video đã upload trong MinIO") from exc

        if object_stat.size <= 0 or object_stat.size > MAX_VIDEO_SIZE:
            raise HTTPException(status_code=400, detail="Dung lượng video thực tế không hợp lệ")
        if object_stat.size != session["declaredFileSize"]:
            raise HTTPException(status_code=400, detail="Dung lượng video khác với thông tin đã khai báo")

        task = crud_task.get(session["taskId"])
        sport = crud_sport.get(session["sportId"])
        user = crud_user.get(user_id)
        if not task or not sport or str(task.course_id) != session["courseId"] or str(task.sport_id) != session["sportId"]:
            raise HTTPException(status_code=400, detail="Thông tin task/course/sport không còn hợp lệ")

        now = datetime.now(timezone.utc)
        job = build_grading_job(
            result_id=result_id,
            sport_code=session["sportCode"],
            mode=session["sportMode"],
            bucket=session["bucket"],
            object_key=session["objectKey"],
            attempt_no=session["attemptNo"],
            duration_sec=session.get("durationSec"),
            file_size=object_stat.size,
        )
        data = {
            "_id": result_id,
            "taskId": session["taskId"],
            "courseId": session["courseId"],
            "sportId": session["sportId"],
            "userId": str(user_id),
            "attemptNo": session["attemptNo"],
            "pending": True,
            "status": "pending",
            "videoUrl": f"{session['bucket']}/{session['objectKey']}",
            "objectKey": session["objectKey"],
            "bucket": session["bucket"],
            "fileName": session["fileName"],
            "fileSize": object_stat.size,
            "contentType": session["contentType"],
            "durationSec": session.get("durationSec"),
            "submittedAt": now,
            "taskTitle": task.title,
            "studentName": user.name if user else None,
            "studentCode": user.user_code if user else None,
            "gradingJob": job,
            "gradingJobStatus": "pending",
            "gradingJobAttempts": 0,
            "gradingJobNextAttemptAt": now,
        }
        try:
            attempt_no = self._insert_with_free_attempt(data, crud_video_result.collection.insert_one)["attemptNo"]
        except DuplicateKeyError:
            # confirm gọi lại cho cùng phiên upload: bài nộp đã được ghi
            existing = crud_video_result.collection.find_one({"_id": result_id})
            if not existing:
                raise
            attempt_no = existing.get("attemptNo", session["attemptNo"])
        sessions.update_one({"_id": upload_oid}, {"$set": {"status": "confirmed", "confirmedAt": now}})
        notification_service.send_notification(
            user_id=str(user_id),
            title=f"Đã nộp bài: {task.title}",
            message=f"Bài nộp lần thứ {attempt_no} đã được xác nhận và đang chờ hệ thống AI xử lý.",
            notif_type=NotificationType.SUBMISSION_RECEIVED,
            link=f"/student/courses/{task.course_id}/grades",
        )
        return VideoResult.model_validate(crud_video_result.collection.find_one({"_id": result_id}))

    def submit_video(self, user_id: str, video_in: VideoResultCreate) -> VideoResult:
        """Sinh viên nộp video bài tập qua URL có sẵn (legacy / metadata)."""
        task, course, next_attempt = self._validate_submission_guards(
            task_id=video_in.task_id,
            user_id=user_id,
            sport_id=video_in.sport_id,
        )

        user = crud_user.get(user_id)
        data = video_in.model_dump(by_alias=True, exclude_unset=True)
        data["userId"] = str(user_id)
        data["attemptNo"] = next_attempt
        data["pending"] = True
        
        # Denormalization (lưu dư thừa)
        data["courseId"] = str(task.course_id)
        data["taskTitle"] = task.title
        if user:
            data["studentName"] = user.name
            data["studentCode"] = user.user_code

        created = self._insert_with_free_attempt(data, crud_video_result.create)
        next_attempt = created.attempt_no

        # Gửi job chấm điểm vào Kafka nếu có video_url
        if video_in.video_url:
            try:
                from app.services.kafka_producer import kafka_producer
                sport = crud_sport.get(video_in.sport_id)
                sport_code = sport.code if sport else "unknown"
                kafka_producer.dispatch_grading_job(
                    result_id=str(created.id),
                    task_id=str(video_in.task_id),
                    sport_id=str(video_in.sport_id),
                    sport_code=sport_code,
                    user_id=str(user_id),
                    video_url=video_in.video_url,
                    attempt_no=next_attempt,
                )
            except Exception as e:
                logger.warning("Could not dispatch Kafka grading job: %s", e)

        # Gửi thông báo sinh viên đã nộp bài thành công
        notification_service.send_notification(
            user_id=str(user_id),
            title=f"Đã nộp bài: {task.title}",
            message=f"Bài nộp lần thứ {next_attempt} của bạn đã được ghi nhận. Hệ thống AI đang tiến hành chấm điểm.",
            notif_type=NotificationType.SUBMISSION_RECEIVED,
            link=f"/student/courses/{task.course_id}/grades",
        )

        return created

    def submit_video_file(
        self,
        user_id: str,
        task_id: str,
        sport_id: str,
        file: UploadFile,
        duration_sec: Optional[int] = None,
    ) -> VideoResult:
        """Upload file video lên MinIO và lưu kết quả bài nộp ở trạng thái pending."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên file không hợp lệ",
            )

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng video không được hỗ trợ ({ext}). Chỉ chấp nhận: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}",
            )

        task, course, next_attempt = self._validate_submission_guards(task_id, user_id, sport_id)

        # Lấy dung lượng từ file tạm (không đọc cả file vào RAM) rồi stream lên MinIO theo từng part
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File video rỗng",
            )
        if file_size > settings.LEGACY_UPLOAD_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=LEGACY_UPLOAD_TOO_LARGE_MESSAGE,
            )

        # Định danh file trên MinIO: {sport_id}/{task_id}/{user_id}_attempt{next_attempt}_{timestamp}{ext}
        timestamp = int(datetime.now(timezone.utc).timestamp())
        object_name = f"{sport_id}/{task_id}/{user_id}_attempt{next_attempt}_{timestamp}{ext}"

        minio_path = minio_service.upload_file(
            file_data=file.file,
            object_name=object_name,
            length=file_size,
            content_type=file.content_type or "video/mp4",
        )

        user = crud_user.get(user_id)
        sport = crud_sport.get(sport_id)
        sport_code = sport.code.upper() if sport else "unknown"
        sport_mode = (sport.mode.value if sport and hasattr(sport.mode, "value") else (sport.mode if sport else "video")).upper()
        now = datetime.now(timezone.utc)

        data = {
            "taskId": str(task_id),
            "sportId": str(sport_id),
            "userId": str(user_id),
            "attemptNo": next_attempt,
            "pending": True,
            "status": "pending",
            "videoUrl": minio_path,
            "bucket": settings.MINIO_BUCKET_NAME,
            "objectKey": object_name,
            "fileName": file.filename,
            "fileSize": file_size,
            "contentType": file.content_type or "video/mp4",
            "durationSec": duration_sec,
            "submittedAt": now,
            # Denormalization (lưu dư thừa)
            "courseId": str(task.course_id),
            "taskTitle": task.title,
            "gradingJob": build_grading_job(
                result_id=None,
                sport_code=sport_code,
                mode=sport_mode,
                bucket=settings.MINIO_BUCKET_NAME,
                object_key=object_name,
                attempt_no=next_attempt,
                duration_sec=duration_sec,
                file_size=file_size,
            ),
            "gradingJobStatus": "pending",
            "gradingJobAttempts": 0,
            "gradingJobNextAttemptAt": now,
        }
        if user:
            data["studentName"] = user.name
            data["studentCode"] = user.user_code

        created = self._insert_with_free_attempt(data, crud_video_result.create)
        next_attempt = created.attempt_no
        result_oid = ObjectId(created.id)
        crud_video_result.collection.update_one(
            {"_id": result_oid},
            {"$set": {"gradingJob.jobId": str(created.id)}}
        )

        notification_service.send_notification(
            user_id=str(user_id),
            title=f"Đã nộp bài: {task.title}",
            message=f"Bài nộp lần thứ {next_attempt} của bạn đã được ghi nhận và lưu trữ an toàn. Hệ thống đang chờ chấm điểm.",
            notif_type=NotificationType.SUBMISSION_RECEIVED,
            link=f"/student/courses/{task.course_id}/grades",
        )

        return created

    def get_presigned_url(self, result_id: str, current_user_id: str, role: str) -> str:
        """Lấy Presigned URL xem video từ MinIO có kiểm tra quyền truy cập."""
        result = self.get_by_id(result_id)
        if role == "student" and result.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập video này",
            )

        if not result.video_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bài nộp này không có video",
            )

        if result.video_url.startswith("http://") or result.video_url.startswith("https://"):
            return result.video_url

        return minio_service.get_presigned_url(result.video_url)

    def get_by_id(self, result_id: str) -> VideoResult:
        """Lấy chi tiết bài nộp video."""
        result = crud_video_result.get(result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy kết quả bài nộp",
            )
        return result

    def ensure_can_view(
        self,
        user_id: str,
        role: str,
        owner_id: Optional[str],
        course_id: Optional[str],
        task_id: Optional[str] = None,
    ) -> None:
        """Chỉ chủ bài nộp, giáo viên của khóa học hoặc admin được xem bài nộp."""
        if role == UserRole.ADMIN.value or (owner_id and str(owner_id) == str(user_id)):
            return
        if role == UserRole.TEACHER.value:
            if not course_id and task_id:
                task = crud_task.get(task_id)
                course_id = task.course_id if task else None
            course = crud_course.get(course_id) if course_id else None
            if course and str(course.teacher_id) == str(user_id):
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem bài nộp này",
        )

    def get_for_user(self, result_id: str, user_id: str, role: str) -> VideoResult:
        """Lấy chi tiết bài nộp có kiểm tra quyền xem."""
        result = self.get_by_id(result_id)
        self.ensure_can_view(user_id, role, result.user_id, result.course_id, result.task_id)
        return result

    def get_status(self, result_id: str, user_id: str, role: str) -> VideoResultStatusResponse:
        """Endpoint polling siêu nhẹ kiểm tra trạng thái bài nộp."""
        obj_id = to_object_id(result_id)
        if not obj_id:
            raise HTTPException(status_code=400, detail="Mã kết quả bài nộp không hợp lệ")

        doc = crud_video_result.collection.find_one(
            {"_id": obj_id},
            {
                "_id": 1, "pending": 1, "status": 1, "error": 1, "aiScore": 1, "finalScore": 1,
                "userId": 1, "courseId": 1, "taskId": 1,
            },
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")
        self.ensure_can_view(user_id, role, doc.get("userId"), doc.get("courseId"), doc.get("taskId"))

        return VideoResultStatusResponse(
            id=str(doc["_id"]),
            pending=doc.get("pending", True),
            status=doc.get("status", "pending"),
            error=doc.get("error"),
            ai_score=doc.get("aiScore"),
            final_score=doc.get("finalScore"),
        )

    def list_results(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        pending: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[VideoResult], int]:
        """Lấy danh sách kết quả nộp video có bộ lọc."""
        query: dict = {}
        if task_id:
            query["taskId"] = str(task_id)
        if user_id:
            query["userId"] = str(user_id)
        if pending is not None:
            query["pending"] = pending

        return crud_video_result.get_multi(filter=query, skip=skip, limit=limit)

    def list_task_submissions(
        self, task_id: str, status_filter: Optional[str] = None
    ) -> list[SubmissionItemResponse]:
        """Lấy danh sách bài nộp của 1 task cho giáo viên kèm thông tin sinh viên."""
        query: dict = {"taskId": str(task_id)}
        if status_filter == "pending":
            query["pending"] = True
        elif status_filter == "ai_graded":
            query["pending"] = False
            query["finalScore"] = None
        elif status_filter == "teacher_graded":
            query["finalScore"] = {"$ne": None}

        cursor = crud_video_result.collection.find(query).sort("submittedAt", -1)
        results = []

        for doc in cursor:
            uid = str(doc.get("userId", ""))
            
            results.append(
                SubmissionItemResponse(
                    id=str(doc["_id"]),
                    user_id=uid,
                    student_code=doc.get("studentCode"),
                    student_name=doc.get("studentName"),
                    attempt_no=doc.get("attemptNo", 1),
                    submitted_at=doc.get("submittedAt"),
                    pending=doc.get("pending", True),
                    video_url=doc.get("videoUrl"),
                    duration_sec=doc.get("durationSec"),
                    metrics=doc.get("metrics", {}),
                    ai_score=doc.get("aiScore"),
                    ai_comment=doc.get("aiComment"),
                    final_score=doc.get("finalScore"),
                    teacher_comment=doc.get("teacherComment"),
                    graded_by=doc.get("gradedBy"),
                    graded_at=doc.get("gradedAt"),
                )
            )

        return results

    def ai_callback(self, result_id: str, ai_in: VideoResultAIUpdate) -> VideoResult:
        """
        AI Worker cập nhật kết quả phân tích.
        Sử dụng Sport Evaluator Strategy để tính điểm và sinh nhận xét nếu AI Worker chưa có.
        """
        result = self.get_by_id(result_id)
        task = crud_task.get(result.task_id)
        sport = crud_sport.get(result.sport_id) if task else None

        # Sử dụng evaluator từ registry nếu aiScore hoặc aiComment chưa có
        evaluator = sport_registry.get_evaluator(sport.code if sport else None)
        if ai_in.ai_score is None and ai_in.metrics:
            ai_in.ai_score = evaluator.calculate_score(ai_in.metrics)
        if not ai_in.ai_comment and ai_in.metrics and ai_in.ai_score is not None:
            ai_in.ai_comment = evaluator.generate_comment(ai_in.metrics, ai_in.ai_score)

        updated = crud_video_result.update_ai_result(result_id, ai_in)
        if not updated:
            # Bài nộp đã có kết quả (kết quả trùng): không tính lại điểm, không gửi thông báo lần nữa
            logger.info("Ignoring duplicate AI result for resultId=%s (already completed)", result_id)
            return self.get_by_id(result_id)

        # Tính điểm đại diện (effective score) dựa trên gradingMethod của task
        effective_score = self._compute_effective_score(result.task_id, result.user_id, task)

        # Đồng bộ điểm vào enrollment
        enrollment_service.update_task_progress(
            user_id=result.user_id,
            task_id=result.task_id,
            score=effective_score,
        )

        # Gửi thông báo đến sinh viên
        notification_service.send_notification(
            user_id=result.user_id,
            title=f"Đã có điểm: {task.title if task else 'Bài tập'}",
            message=f"Hệ thống AI đã chấm điểm bài tập của bạn: {ai_in.ai_score} điểm. Nhận xét: {ai_in.ai_comment}",
            notif_type=NotificationType.SUBMISSION_GRADED,
            link=f"/student/courses/{task.course_id if task else ''}/grades",
        )

        return updated

    def ai_failure(self, result_id: str, error_code: str) -> VideoResult:
        """Persist a terminal AI failure without exposing worker exception details."""
        updated = crud_video_result.mark_failed(result_id, error_code[:100])
        if not updated:
            # Không tìm thấy (404) hoặc đã completed thì giữ nguyên kết quả completed
            existing = self.get_by_id(result_id)
            logger.info("Ignoring late AI failure for resultId=%s (status=%s)", result_id, existing.status)
            return existing
        return updated

    def teacher_grade(
        self,
        result_id: str,
        teacher_id: str,
        grade_in: VideoResultTeacherGrade,
    ) -> VideoResult:
        """Giáo viên chấm điểm thủ công hoặc override điểm AI."""
        result = self.get_by_id(result_id)
        task = crud_task.get(result.task_id)

        grade_in.graded_by = str(teacher_id)
        updated = crud_video_result.teacher_grade(result_id, grade_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chấm điểm thất bại",
            )

        # Tính lại điểm đại diện
        effective_score = self._compute_effective_score(result.task_id, result.user_id, task)

        enrollment_service.update_task_progress(
            user_id=result.user_id,
            task_id=result.task_id,
            score=effective_score,
        )

        # Gửi thông báo đến sinh viên
        notification_service.send_notification(
            user_id=result.user_id,
            title=f"Giảng viên đã chấm: {task.title if task else 'Bài tập'}",
            message=f"Giảng viên đã đánh giá bài nộp của bạn: {grade_in.final_score} điểm.",
            notif_type=NotificationType.SUBMISSION_GRADED,
            link=f"/student/courses/{task.course_id if task else ''}/grades",
        )

        return updated

    def _compute_effective_score(self, task_id: str, user_id: str, task: Optional[Task]) -> float:
        """Tính điểm đại diện dựa trên gradingMethod: highest, latest, average."""
        attempts = list(
            crud_video_result.collection.find(
                {"taskId": str(task_id), "userId": str(user_id)},
                {"finalScore": 1, "aiScore": 1, "submittedAt": 1},
            ).sort("submittedAt", 1)
        )
        if not attempts:
            return 0.0

        scores = []
        for a in attempts:
            s = a.get("finalScore") if a.get("finalScore") is not None else a.get("aiScore")
            if s is not None:
                scores.append(float(s))

        if not scores:
            return 0.0

        method = getattr(task, "grading_method", GradingMethod.HIGHEST)
        if method == GradingMethod.HIGHEST:
            return max(scores)
        elif method == GradingMethod.LATEST:
            return scores[-1]
        elif method == GradingMethod.AVERAGE:
            return round(sum(scores) / len(scores), 2)

        return max(scores)


video_result_service = VideoResultService()
