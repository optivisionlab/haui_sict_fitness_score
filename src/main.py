import uvicorn
from fastapi import FastAPI
from src.api.sub_api import search

app = FastAPI()

# Include routes từ file khác
app.include_router(search.router)

if __name__ == "__main__":
       uvicorn.run("main:app", host="0.0.0.0", port=8000)