from pydantic import BaseModel, Field
from typing import List

class StudentTrackingInput(BaseModel):
    id: List[int] = Field(default=[0,1,2])
    bbox: List[List[int]] = Field(default= [[1,1,1,1], [1,1,1,1]])