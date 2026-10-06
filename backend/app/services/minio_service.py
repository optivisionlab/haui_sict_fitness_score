import io
import logging
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinioService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.default_bucket = settings.MINIO_BUCKET_NAME

    def ensure_bucket(self, bucket_name: str | None = None) -> None:
        bucket = bucket_name or self.default_bucket
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created MinIO bucket: %s", bucket)
        except S3Error as e:
            logger.error("Error ensuring MinIO bucket '%s': %s", bucket, e)
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        length: int,
        content_type: str = "video/mp4",
        bucket_name: str | None = None,
    ) -> str:
        bucket = bucket_name or self.default_bucket
        self.ensure_bucket(bucket)
        try:
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=file_data,
                length=length,
                content_type=content_type,
            )
            return f"{bucket}/{object_name}"
        except S3Error as e:
            logger.error("Failed to upload object '%s' to MinIO bucket '%s': %s", object_name, bucket, e)
            raise

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "video/mp4",
        bucket_name: str | None = None,
    ) -> str:
        return self.upload_file(
            file_data=io.BytesIO(data),
            object_name=object_name,
            length=len(data),
            content_type=content_type,
            bucket_name=bucket_name,
        )

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=2),
        bucket_name: str | None = None,
    ) -> str:
        bucket = bucket_name or self.default_bucket
        # If object_name includes bucket prefix like "videos/user_id/...", extract clean object_name
        if object_name.startswith(f"{bucket}/"):
            clean_name = object_name[len(bucket) + 1 :]
        else:
            clean_name = object_name

        try:
            return self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=clean_name,
                expires=expires,
            )
        except S3Error as e:
            logger.error("Failed to generate presigned URL for '%s': %s", clean_name, e)
            raise

    def delete_file(self, object_name: str, bucket_name: str | None = None) -> bool:
        bucket = bucket_name or self.default_bucket
        if object_name.startswith(f"{bucket}/"):
            clean_name = object_name[len(bucket) + 1 :]
        else:
            clean_name = object_name

        try:
            self.client.remove_object(bucket_name=bucket, object_name=clean_name)
            return True
        except S3Error as e:
            logger.error("Failed to delete object '%s' from MinIO: %s", clean_name, e)
            return False


minio_service = MinioService()
