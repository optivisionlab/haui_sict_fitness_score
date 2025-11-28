import uvicorn
from fastapi import FastAPI, Request
from src.api.sub_api import search, mongo_search
import torch
import gc

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
        import torch
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        gc.collect()
        print("GPU memory cleaned")


if __name__ == "__main__":
       uvicorn.run("main:app", host="0.0.0.0", port=8000)