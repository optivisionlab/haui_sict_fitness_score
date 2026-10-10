import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, UploadFile, status
from app.crud.base import to_object_id
from app.crud.course import crud_course
from app.crud.enrollment import crud_enrollment
from app.crud.sport import crud_sport
from app.crud.task import crud_task
from app.crud.user import crud_user
from app.crud.video_result import crud_video_result
from app.models.course import Course
from app.models.notification import NotificationType
from app.models.sport import SportMode
from app.models.task import GradingMethod, Task, TaskCategory
from app.models.video_result import VideoResult
from app.schemas.video_result import (
    SubmissionItemResponse,
    VideoResultAIUpdate,
    VideoResultCreate,
    VideoResultStatusResponse,
    VideoResultTeacherGrade,
)
from app.services.enrollment_service import enrollment_service
from app.services.minio_service import minio_service
from app.services.notification_service import notification_service
from app.services.sports.registry import sport_registry

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB

logger = logging.getLogger(__name__)


class VideoResultService:
    def _validate_submission_guards(
        self, task_id: str, user_id: str, sport_id: str
    ) -> tuple[Task, Course, int]:
        """
        4 Lớp Bảo Vệ (4-Layer Guards):
        1. Kiểm tra lớp đã chốt sổ điểm chưa.
        2. Kiểm tra cờ khóa nộp bài cấp lớp (allowPracticeSubmission / allowExamSubmission).
        3. Kiểm tra bài tập có bị khóa hoặc ngoài khung giờ nộp bài.
        4. Kiểm tra giới hạn số lần nộp (maxAttempts).
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

        # GUARD 4: Kiểm tra giới hạn số lần nộp bài (maxAttempts)
        existing_count = crud_video_result.collection.count_documents({
            "taskId": str(task_id),
            "userId": str(user_id),
        })
        if getattr(task, "max_attempts", None) and existing_count >= task.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bạn đã hết lượt nộp bài cho phép ({existing_count}/{task.max_attempts} lần)",
            )

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

        next_attempt = existing_count + 1
        return task, course, next_attempt

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

        created = crud_video_result.create(data)

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

        # Đọc dữ liệu file và kiểm tra dung lượng
        file_bytes = file.file.read()
        file_size = len(file_bytes)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File video rỗng",
            )
        if file_size > MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dung lượng video vượt quá giới hạn cho phép (500MB)",
            )

        # Định danh file trên MinIO: {sport_id}/{task_id}/{user_id}_attempt{next_attempt}_{timestamp}{ext}
        timestamp = int(datetime.now(timezone.utc).timestamp())
        object_name = f"{sport_id}/{task_id}/{user_id}_attempt{next_attempt}_{timestamp}{ext}"

        minio_path = minio_service.upload_bytes(
            data=file_bytes,
            object_name=object_name,
            content_type=file.content_type or "video/mp4",
        )

        user = crud_user.get(user_id)
        data = {
            "taskId": str(task_id),
            "sportId": str(sport_id),
            "userId": str(user_id),
            "attemptNo": next_attempt,
            "pending": True,
            "videoUrl": minio_path,
            "fileName": file.filename,
            "fileSize": file_size,
            "contentType": file.content_type or "video/mp4",
            "durationSec": duration_sec,
            "submittedAt": datetime.now(timezone.utc),
            # Denormalization (lưu dư thừa)
            "courseId": str(task.course_id),
            "taskTitle": task.title,
        }
        if user:
            data["studentName"] = user.name
            data["studentCode"] = user.user_code

        created = crud_video_result.create(data)

        # Gửi job chấm điểm vào Kafka
        try:
            from app.services.kafka_producer import kafka_producer
            sport = crud_sport.get(sport_id)
            sport_code = sport.code if sport else "unknown"
            kafka_producer.dispatch_grading_job(
                result_id=str(created.id),
                task_id=str(task_id),
                sport_id=str(sport_id),
                sport_code=sport_code,
                user_id=str(user_id),
                video_url=minio_path,
                attempt_no=next_attempt,
            )
        except Exception as e:
            logger.warning("Could not dispatch Kafka grading job: %s", e)

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

    def get_status(self, result_id: str) -> VideoResultStatusResponse:
        """Endpoint polling siêu nhẹ kiểm tra trạng thái bài nộp."""
        obj_id = to_object_id(result_id)
        if not obj_id:
            raise HTTPException(status_code=400, detail="Mã kết quả bài nộp không hợp lệ")

        doc = crud_video_result.collection.find_one(
            {"_id": obj_id},
            {"_id": 1, "pending": 1, "aiScore": 1, "finalScore": 1},
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")

        return VideoResultStatusResponse(
            id=str(doc["_id"]),
            pending=doc.get("pending", True),
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật kết quả AI thất bại",
            )

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
