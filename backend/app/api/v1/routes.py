from fastapi import APIRouter

from app.api.v1.endpoints import chat, session

api_router = APIRouter()
api_router.include_router(
    chat.router, prefix="/chat", tags=["chat-endpoints"]
)
api_router.include_router(
    session.router, prefix="/session", tags=["session-endpoints"]
)
