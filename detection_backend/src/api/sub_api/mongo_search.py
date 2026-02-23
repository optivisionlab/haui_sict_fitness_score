from fastapi import APIRouter, HTTPException
from pydantic import HttpUrl, BaseModel
from loguru import logger
import json
from pymongo.errors import PyMongoError

from src.models.search_input_params import InsertRequest
from src.database.mongo import MongoDBManager

router = APIRouter()

@router.post("/data/insert")
def insert_data(request: InsertRequest):
    client = MongoDBManager()
    try:
        if not request.data:
                raise HTTPException(status_code=400, detail="Data list is empty")

        result = client.insert_many(collection_name=request.collection_name,documents=request.data)

        return {
            "status_code" : 200,
            "status": "success",
            "inserted_ids": [str(_id) for _id in result]
        }
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")