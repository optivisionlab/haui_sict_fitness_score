from pydantic import BaseModel, Field
from typing import List, Dict, Any

class StudentTrackingInput(BaseModel):
    id: List[int] = Field(default=[0,1])
    bbox: List[List[int]] = Field(default= [[1,1,1,1], [1,1,1,1]])

class InsertRequest(BaseModel):
    collection_name: str
    data: List[Dict[str, Any]]