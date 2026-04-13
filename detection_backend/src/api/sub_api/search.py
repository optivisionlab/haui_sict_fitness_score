from fastapi import APIRouter, UploadFile, File, Form, status, BackgroundTasks
from typing import List
from PIL import Image
import requests
from io import BytesIO
from pydantic import HttpUrl
from loguru import logger
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from urllib.parse import quote_plus
import asyncio
import redis
import os
from datetime import datetime
import time


from src.config.depend import *
from fastapi.responses import JSONResponse
from src.database.qdrant import QdrantVectorStore
from src.models.search_input_params import StudentTrackingInput
from src.app.embedding.facenet_embedding import get_embedding
from src.app.query_process import stream_redisresults

qdrant_db = QdrantVectorStore()
router = APIRouter()

stop_flag = True   
is_running = False 



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
    tracking_frame: str = Form(None),
    similarity_threshold: float = Form(0.65)
):
    start_time = time.time()
    try:
        tracking_data = tracking_frame
        if tracking_frame:
            try:
                tracking_data = StudentTrackingInput.model_validate(json.loads(tracking_frame))
            except Exception as e:
                return {"error": f"Invalid tracking_frame format: {e}"}
        pil_images = None

        if images:
            pil_images = load_image_from_upload(images)

        elif image_urls:
            pil_images = load_image_from_url(str(image_urls))

        if not pil_images:
            return {"error": "No valid image input"}

        tracking_object = []

        logger.info("tracking_frame: {}", tracking_frame)

        for bbox in tracking_data.bbox:
            images_person = pil_images.crop(bbox)
            tracking_object.append(images_person)
            now = datetime.now()
            if DEBUG_MODE:
                os.makedirs("../tmp", exist_ok=True)
                images_person.save(f"../tmp/{now.strftime('%Y_%m_%d_%H_%M_%S')}.png")

        search_data = qdrant_db.get_relevant_faces(query=tracking_object, collection_name=collection_name, k = 1, threshold= similarity_threshold)

        result_data = []
        for id, student_data in zip(tracking_data.id, search_data):
            result_data.append({'id' : id, "infor" : student_data if student_data else None})
        
        return JSONResponse(content={'status_code' : 200, 'status': "insert oke", "data": result_data}, status_code= status.HTTP_200_OK)
    finally:
        logger.debug(f"Face search Backend Time: {time.time() - start_time}")
    # else:
    #     return JSONResponse(content={'status_code' : 422, 'status': "Search failt", "data": None}, status_code= status.HTTP_422_UNPROCESSABLE_ENTITY)

@router.post("/faces/emb")
async def face_emb(
    images: UploadFile = File(None),
    image_urls: HttpUrl = Form(None),
):
    if images:
        pil_images = load_image_from_upload(images)

    elif image_urls:
        pil_images = load_image_from_url(str(image_urls))

    if not pil_images:
        return {"error": "No valid image input"}
    
    emb_list = get_embedding(images=[pil_images], verbose=True)
    for emb in emb_list:
        logger.debug("embedidng shape: {}", emb.shape if emb is not None else None)
        
    return JSONResponse(content={'status_code' : 200, 'status': "insert oke"}, status_code= status.HTTP_200_OK)

async def background_job(sleeptime : int = 3):
    global stop_flag, is_running

    if not stop_flag:
        is_running = False
        return

    logger.info("Bắt đầu tiến trình đọc dữ liệu...")
    r = redis.Redis(
        host='10.100.200.119',
        port=6379,
        db=0,  # mặc định
        password='optivisionlab',
        decode_responses=True  # để trả về string thay vì bytes
    )
    DATABASE_URL = f"postgresql://labelstudio:{quote_plus('Admin@221b')}@10.100.200.119:5555/fitness_db"
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        for row in stream_redisresults(session):
            student_infor = row
            KEY = student_infor.user_id
            new_data = row.to_dict()
            logger.info('new_data: {}', new_data)
            new_data.pop('id')
            if not stop_flag:
                logger.info("STOP FLAG = FALSE → DỪNG TIẾN TRÌNH.")
                r.delete(KEY)
                break
            
            await asyncio.sleep(sleeptime)
            raw = r.hgetall(name = KEY)
            if raw:
                old_data = raw
            else:
                old_data = {}
            old_data.update(new_data)
            r.hset(KEY, mapping= old_data)

            
    logger.info("Tiến trình đã kết thúc.")
    is_running = False


@router.post("/start")
async def start_job(background_tasks: BackgroundTasks, sleeptime: int = 3):
    global stop_flag, is_running

    # Nếu job đang chạy, không cho chạy tiếp
    if is_running:
        return {"message": "Job is already running"}

    stop_flag = True
    is_running = True
    background_tasks.add_task(background_job, sleeptime)
    return {"message": "Job started"}


@router.post("/stop")
async def stop_job():
    global stop_flag
    stop_flag = False
    return {"message": "Stop flag set to FALSE. Job will stop immediately."}