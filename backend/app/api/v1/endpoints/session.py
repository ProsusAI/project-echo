import logging
from io import BytesIO
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel
from datetime import datetime

from app.models.session_model import Session
from app.utils.aws_utils import create_presigned_url, S3_BUCKET_NAME, S3_KEY_TEMPLATE, \
    resize_and_replace_image, upload_bytes_to_s3

logger = logging.getLogger(__name__)

router = APIRouter()

class CharacterInfo(BaseModel):
    name: str
    photo_url: str

class SessionResponse(BaseModel):
    id: int
    last_update_datetime: datetime
    content_title: Optional[str] = None
    content_subtitle: Optional[str] = None
    content_type: Optional[str] = None
    content_description: Optional[str] = None
    number_of_scenes: Optional[int] = None
    characters: List[CharacterInfo] = []

    class Config:
        from_attributes = True

class UploadFileToSession(BaseModel):
    session_id: int
    s3_key: str
    file_type: str

    class Config:
        from_attributes = True

@router.get("/sessions/", response_model=List[SessionResponse])
async def get_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=50)
):
    """Get all sessions with pagination."""
    sessions = Session.objects.order_by('-last_update_datetime').skip(skip).limit(limit)
    
    response = []
    for session in sessions:
        if session.messages and len(session.messages) > 0:
            session_data = {
                "id": session.id,
                "last_update_datetime": session.last_update_datetime,
                "content_title": session.content_title or "Untitled Session",
                "content_subtitle": session.content_subtitle,
                "content_type": session.content_outline.get("content_type") if session.content_outline else None,
                "content_description": session.content_outline.get("content_description") if session.content_outline else None,
                "number_of_scenes": session.content_outline.get("number_of_scenes") if session.content_outline else None,
                "characters": [
                    {"name": char.name, "photo_url": char.photo_url}
                    for char in session.characters_created
                    if char.photo_url
                ]
            }
            response.append(SessionResponse(**session_data))
    
    return response

@router.put("/upload/{file_path}")
async def upload_file_to_s3(file_path: str, session_id: int, request: Request):
    logger.info(f"Received request to upload file to s3")
    file_body = await request.body()
    session = Session.objects(id=session_id).first()
    file_s3_key = S3_KEY_TEMPLATE.format(demo_name=session.demo_name,
                                         session_id=session.id,
                                         filename=file_path)
    
    file_data = BytesIO(file_body)
    await upload_bytes_to_s3(file_data, S3_BUCKET_NAME, file_s3_key)
    return {"file_s3_key": file_s3_key}


@router.post("/add_file_to_session/")
def add_file_to_session(upload_file: UploadFileToSession):
    session = Session.objects(id=upload_file.session_id).first()
    if not session:
        return HTTPException(status_code=404, detail="Session not found")

    if upload_file.file_type == "image":
        resize_and_replace_image(upload_file.s3_key)

    filename = upload_file.s3_key.split("/")[-1]

    file_presigned_url = create_presigned_url(bucket_name=S3_BUCKET_NAME, s3_key=upload_file.s3_key)
    session.add_uploaded_file(filename, upload_file.s3_key, file_presigned_url)

    file_presigned_url = file_presigned_url.replace("/minio:", "/localhost:")
    return {"file_presigned_url": file_presigned_url}


@router.delete("/remove_file_from_session/")
def remove_file_from_session(session_id: int = Query(...), file_name: str = Query(...)):
    session = Session.objects(id=session_id).first()
    if not session:
        return HTTPException(status_code=404, detail="Session not found")

    session.remove_uploaded_file(file_name)
    return {"message": "File removed from session"}

@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    """Get a specific session with all its data."""
    session = Session.objects(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session.load_conversation()
    
    # Convert messages to dict with all required fields
    messages = []
    for message in session.messages:
        message_dict = message.to_mongo().to_dict()
        # Ensure all required fields are present
        if 'text' not in message_dict:
            message_dict['text'] = ''
        if 'timestamp' not in message_dict:
            logger.info(f"Message ID: {message_dict.get('_id')}")
            message_dict['timestamp'] = message_dict.get('_id').generation_time
        messages.append(message_dict)
    
    return {
        "id": session.id,
        "messages": messages,
        "characters_created": [char.to_mongo().to_dict() for char in session.characters_created],
        "audio_segments": [segment.to_mongo().to_dict() for segment in session.audio_segments],
        "content_title": session.content_title,
        "content_subtitle": session.content_subtitle,
        "content_outline": session.content_outline,
        "last_update_datetime": session.last_update_datetime
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    """Delete a specific session and all its associated files."""
    session = Session.objects(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Delete the session (this will trigger the pre_delete hook)
        session.delete()
        return {"message": f"Session {session_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")
