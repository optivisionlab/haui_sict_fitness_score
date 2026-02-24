# Load model file
# from src.database.mongo import MongoDBManager
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
from src.database.minio_client import MinioClient


# mongo_db = MongoDBManager()

class UserTrack(BaseModel):
    user_id: str
    exam_id: Optional[Any] = None
    step: Optional[Any] = None
    start_time: Optional[Any] = None
    end_time: Optional[Any] = None

class BatchTrackRequest(BaseModel):
    users: List[UserTrack]

minio_client = MinioClient()