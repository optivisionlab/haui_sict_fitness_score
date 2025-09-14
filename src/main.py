import uvicorn
from fastapi import FastAPI
from src.api.sub_api import search, mongo_search

app = FastAPI()

# Include routes từ file khác
app.include_router(search.router)
app.include_router(mongo_search.router)


if __name__ == "__main__":
       uvicorn.run("main:app", host="0.0.0.0", port=8000)