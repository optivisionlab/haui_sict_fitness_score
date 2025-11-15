# Load model file
# from src.database.mongo import MongoDBManager
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


# mongo_db = MongoDBManager()

class UserTrack(BaseModel):
    user_id: str
    exam_id: Optional[str] = None
    step: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class BatchTrackRequest(BaseModel):
    users: List[UserTrack]