import uvicorn
from fastapi import FastAPI, Request
from src.api.sub_api import search, mongo_search
from src.config.configs import DEVICE
import torch
import gc
import os


app = FastAPI()

# Include routes từ file khác
app.include_router(search.router)
app.include_router(mongo_search.router)

@app.middleware("http")
async def cleanup_after_request(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    finally:
        if "cuda" in DEVICE:
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        gc.collect()
        print("GPU memory cleaned")


if __name__ == "__main__":
       uvicorn.run("main:app", host="0.0.0.0", port=os.getenv("API_PORT", 8000))