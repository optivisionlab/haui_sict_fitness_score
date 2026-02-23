from minio import Minio
from loguru import logger
from typing import Union
import numpy as np
from PIL import Image
import io
from src.config.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_NAME


class MinioClient:
    def __init__(self, endpoint = MINIO_ENDPOINT, 
                 access_key = MINIO_ACCESS_KEY, 
                 secret_key = MINIO_SECRET_KEY,
                 bucket_name = MINIO_BUCKET_NAME):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )

        self.bucket_name = bucket_name

        found = self.client.bucket_exists(bucket_name=self.bucket_name)
        if not found:
            self.client.make_bucket(bucket_name=self.bucket_name)
            logger.info("Created bucket: {}", self.bucket_name)
        else:
            logger.info("Bucket: {} already exists", self.bucket_name)

    def push_data(self, image:np.array, destination_file:str):
        buffer = io.BytesIO()
        image = Image.fromarray(image)
        image.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        size = len(image_bytes)

        self.client.put_object(
            self.bucket_name,
            destination_file,
            io.BytesIO(image_bytes),
            size,
            content_type="image/jpeg"
        )
        return self.client.presigned_get_object(self.bucket_name, destination_file)
    
if __name__ == "__main__":
    cline = MinioClient()
    image = Image.open("/home/chuhuyhoang/code/haui_sict_fitness_score/tmp/jakc-4-1150.jpg")
    cline.push_data(image=image, destination_file='test/test.jpg')