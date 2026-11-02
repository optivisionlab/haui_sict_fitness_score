import io
from unittest.mock import MagicMock, PropertyMock, patch
from bson import ObjectId
from fastapi import UploadFile

from app.models.task import Task, TaskCategory
from app.services.task_service import task_service, ALLOWED_INSTRUCTION_VIDEO_EXTENSIONS, MAX_INSTRUCTION_VIDEO_BYTES


def test_instruction_video_logic():
    print(">>> KIỂM THỬ TÍNH NĂNG HƯỚNG DẪN SOẠN BÀI (INSTRUCTION VIDEO)")

    dummy_task = Task(
        id=ObjectId("507f1f77bcf86cd799439011"),
        course_id="507f1f77bcf86cd799439012",
        sport_id="507f1f77bcf86cd799439013",
        title="Thi Giữa Kỳ Pickleball",
        category=TaskCategory.EXAM,
    )

    # 1. Kiểm tra validation định dạng file
    fake_bad_file = UploadFile(
        file=io.BytesIO(b"abc"),
        filename="test.exe",
        headers={"content-type": "application/octet-stream"},
    )
    with patch.object(task_service, "get_by_id", return_value=dummy_task):
        try:
            task_service.upload_instruction_video(task_id="507f1f77bcf86cd799439011", file=fake_bad_file)
            raise AssertionError("Phải báo lỗi khi upload đuôi .exe")
        except Exception as e:
            assert "không được hỗ trợ" in str(e) or "400" in str(e)
            print("  ✓ Đã chặn đúng file không hợp lệ (.exe)")

    fake_video = UploadFile(
        file=io.BytesIO(b"fake video content mp4"),
        filename="guide.mp4",
        headers={"content-type": "video/mp4"},
    )

    mock_collection = MagicMock()
    mock_collection.find_one_and_update.return_value = {
        "_id": ObjectId("507f1f77bcf86cd799439011"),
        "courseId": "507f1f77bcf86cd799439012",
        "sportId": "507f1f77bcf86cd799439013",
        "title": "Thi Giữa Kỳ Pickleball",
        "category": "exam",
        "instructionVideoUrl": "videos/instructions/guide.mp4",
    }

    with patch.object(task_service, "get_by_id", return_value=dummy_task), \
         patch("app.crud.task.CRUDTask.collection", new_callable=PropertyMock, return_value=mock_collection), \
         patch("app.services.task_service.minio_service.upload_file", return_value="videos/instructions/guide.mp4"), \
         patch("app.services.task_service.minio_service.get_presigned_url", return_value="http://minio/videos/instructions/guide.mp4?sign=xyz"):

        mock_collection.find_one_and_update.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "courseId": "507f1f77bcf86cd799439012",
            "sportId": "507f1f77bcf86cd799439013",
            "title": "Thi Giữa Kỳ Pickleball",
            "category": "exam",
            "instructionVideoUrl": "videos/instructions/guide.mp4",
        }

        updated = task_service.upload_instruction_video("507f1f77bcf86cd799439011", fake_video)
        assert updated.instruction_video_url == "videos/instructions/guide.mp4"
        print("  ✓ Upload video hướng dẫn lên MinIO và lưu vào Task thành công")

        # 3. Kiểm tra resolve_video_url sinh Presigned URL
        presigned = task_service.resolve_video_url(updated.instruction_video_url)
        assert "sign=xyz" in presigned
        print("  ✓ Presigned URL sinh thành công để phát video trên trình duyệt")

        # 4. Kiểm tra to_read_dto tự động resolve video URL
        mock_sport_col = MagicMock()
        mock_sport_col.find.return_value = []
        mock_vr_col = MagicMock()
        mock_vr_col.aggregate.return_value = []

        with patch("app.crud.sport.CRUDSport.collection", new_callable=PropertyMock, return_value=mock_sport_col), \
             patch("app.crud.video_result.CRUDVideoResult.collection", new_callable=PropertyMock, return_value=mock_vr_col):
            dto = task_service.to_read_dto(updated)
            assert dto.instruction_video_url == presigned
            print("  ✓ TaskRead DTO chứa URL xem trước video hoàn chỉnh")

        # 5. Kiểm tra xóa video
        dummy_task.instruction_video_url = "videos/instructions/guide.mp4"
        with patch("app.services.task_service.minio_service.delete_file") as mock_delete:
            mock_collection.find_one_and_update.return_value["instructionVideoUrl"] = None
            deleted_task = task_service.delete_instruction_video("507f1f77bcf86cd799439011")
            mock_delete.assert_called_once_with("videos/instructions/guide.mp4")
            assert deleted_task.instruction_video_url is None
            print("  ✓ Xóa video trên MinIO và gỡ bỏ khỏi Task thành công")

    print("\n>>> TẤT CẢ TEST INSTRUCTION VIDEO ĐỀU VƯỢT QUA 100%!")


if __name__ == "__main__":
    test_instruction_video_logic()
