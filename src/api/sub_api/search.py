from fastapi import APIRouter, UploadFile, File, Form, status
from typing import List, Optional, Dict
from PIL import Image
import requests
from io import BytesIO
from pydantic import HttpUrl
from loguru import logger
import json

from src.config.depend import *
from fastapi.responses import JSONResponse
from src.database.qdrant import QdrantVectorStore
from src.models.search_input_params import StudentTrackingInput

qdrant_db = QdrantVectorStore()
router = APIRouter()

def load_image_from_url(url: str) -> Image.Image:
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content)).convert("RGB")

def load_image_from_upload(file: UploadFile) -> Image.Image:
    return Image.open(file.file).convert("RGB")

@router.post("/faces/index")
async def index_face(
    images: List[UploadFile] = File(None),
    image_urls: List[HttpUrl] = Form(None),
    collection_name: str = Form(None),
    data: List[str] = Form([])
):
    pil_images = []

    logger.info("data: {}", data)

    if images:
        for image in images:
            pil_images.append(load_image_from_upload(image))

    elif image_urls:
        for url in image_urls:
            pil_images.append(load_image_from_url(str(url)))

    if not pil_images:
        return {"error": "No valid image input"}

    data = list(map(lambda x : json.loads(x), data))

    insert_status = qdrant_db.add_vector(images=pil_images, collection_name=collection_name, metadata=data)

    if insert_status:
        return JSONResponse(content={'status_code' : 200, 'status': "insert oke"}, status_code= status.HTTP_200_OK)
    else:
        return JSONResponse(content={'status_code' : 422, 'status': "Insert failt"}, status_code= status.HTTP_422_UNPROCESSABLE_ENTITY)
    

@router.post("/faces/search")
async def search_face(
    images: UploadFile = File(None),
    image_urls: HttpUrl = Form(None),
    collection_name: str = Form(None),
    tracking_frame: StudentTrackingInput = Form(None)
):
    pil_images = None

    logger.debug("images: {}", images)

    if images:
        pil_images.append(load_image_from_upload(images))

    elif image_urls:
        pil_images.append(load_image_from_url(str(image_urls)))

    if not pil_images:
        return {"error": "No valid image input"}

    tracking_object = []

    for bbox in tracking_frame.get("bbox", []):
        tracking_object.append(pil_images.crop(bbox))

    search_data = qdrant_db.get_relevant_faces(query=tracking_object, collection_name=collection_name, k = 1)

    # for id, 


    if search_data:
        return JSONResponse(content={'status_code' : 200, 'status': "insert oke", "data": search_data}, status_code= status.HTTP_200_OK)
    else:
        return JSONResponse(content={'status_code' : 422, 'status': "Insert failt", "data": None}, status_code= status.HTTP_422_UNPROCESSABLE_ENTITY)