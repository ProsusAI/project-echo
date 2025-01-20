import os

from dotenv import load_dotenv

from app.config import get_settings

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import mongoengine
from logging_config import logging_config

import logging.config
from app.api.v1.routes import api_router

logging.config.dictConfig(logging_config)

logger = logging.getLogger("main")

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
# app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Assistant API"}


@app.on_event("startup")
async def connect_to_db():
    mongoengine.connect(host=get_settings().database_url, alias="default")

@app.on_event("shutdown")
async def disconnect_from_db():
    mongoengine.disconnect("default")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)