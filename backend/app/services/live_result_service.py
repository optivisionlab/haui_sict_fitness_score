from typing import Any, Optional
from fastapi import HTTPException, status

from app.crud.camera import crud_camera
from app.crud.live_result import crud_live_result
from app.crud.sport import crud_sport
from app.crud.task import crud_task
from app.crud.user import crud_user
from app.models.live_result import LiveResult
from app.models.sport import SportMode
from app.schemas.live_result import LiveResultCreate, LiveResultUpdate
from app.services.enrollment_service import enrollment_service


class LiveResultService:
    def start_session(self, live_in: LiveResultCreate) -> LiveResult:
        """Bắt đầu phiên thi trực tiếp tại sân qua camera."""
        # Kiểm tra user
        if not crud_user.exists(live_in.user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thí sinh ID {live_in.user_id}",
            )

        # Kiểm tra task
        task = crud_task.get(live_in.task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bài thi ID {live_in.task_id}",
            )

        # Kiểm tra sport
        sport = crud_sport.get(live_in.sport_id)
        if not sport or sport.mode != SportMode.CAMERA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Môn thể thao không hợp lệ hoặc không thuộc hình thức thi camera",
            )

        # Kiểm tra camera
        if not crud_camera.exists(live_in.camera_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy thiết bị camera ID {live_in.camera_id}",
            )

        return crud_live_result.create(live_in)

    def get_by_id(self, result_id: str) -> LiveResult:
        """Lấy chi tiết phiên thi trực tiếp."""
        result = crud_live_result.get(result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên thi trực tiếp",
            )
        return result

    def update_session(self, result_id: str, update_in: LiveResultUpdate) -> LiveResult:
        """Cập nhật dữ liệu chỉ số thời gian thực từ camera AI."""
        self.get_by_id(result_id)
        updated = crud_live_result.update(result_id, update_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật phiên thi thất bại",
            )
        return updated

    def finish_session(
        self,
        result_id: str,
        score: Optional[float] = None,
        metrics: Optional[dict[str, Any]] = None,
    ) -> LiveResult:
        """Kết thúc phiên thi trực tiếp, ghi nhận điểm và cập nhật tiến độ học tập."""
        result = self.get_by_id(result_id)
        updated = crud_live_result.finish_session(result_id, score=score, metrics=metrics)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kết thúc phiên thi thất bại",
            )

        if score is not None:
            enrollment_service.update_task_progress(
                user_id=result.user_id,
                task_id=result.task_id,
                score=score,
            )

        return updated

    def list_results(
        self,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[LiveResult], int]:
        """Lấy danh sách kết quả thi trực tiếp."""
        query: dict = {}
        if task_id:
            query["taskId"] = str(task_id)
        if user_id:
            query["userId"] = str(user_id)
        if camera_id:
            query["cameraId"] = str(camera_id)

        return crud_live_result.get_multi(filter=query, skip=skip, limit=limit)


live_result_service = LiveResultService()
