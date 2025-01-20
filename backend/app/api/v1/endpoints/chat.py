import logging
import traceback

import litellm
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.agents import Agent, VoiceDirector, agent_router
from app.core.llm_integration.response_handling import ResponseHandler
from app.config import demo_configuration
from app.models.session_model import Session, MessageType, DemoName

logger = logging.getLogger("websocket_service")

router = APIRouter()

litellm.set_verbose = False


async def get_or_create_session(session_id: str = None) -> Session:
    if session_id:
        session = Session.objects(id=session_id).first()
    else:
        session = Session()
        session.save()
    return session


@router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        session_id: str = None,
):
    logger.info(f"WebSocket connection initiated with session_id: {session_id}")
    session = await get_or_create_session(session_id=session_id)
    logger.info(f"New WebSocket connection with session_id: {session.id}")
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection accepted")
        
        demo_config = demo_configuration
        agent_name = VoiceDirector.workflow

        agent = agent_router[agent_name](demo_configuration=demo_config)
        await websocket.send_json(
            {
                "message_type": "new_session_connected",
                "session_id": session.id,
            }
        )

        while True:
            images_uploaded = []
            data = await websocket.receive_json()
            logger.info(f"Received data: {data}")
            message_type, content = data.get("message_type"), data.get("content")

            if "files" in data and "images" in data["files"] and len(data["files"]["images"]) > 0:
                images_dict_list = data["files"]["images"]
                images_uploaded = [
                    image_dict["url"]
                    for image_dict in images_dict_list
                ]

            if message_type == "user_message":
                logger.info(f"Received user message: {content}")
                session = Session.objects(id=session.id).first()
                session.add_message(MessageType.USER, content)
                await handle_user_message(websocket, session, agent, user_message=content,
                                          images_uploaded=images_uploaded)
                await session.save_conversation()
            elif message_type == "audio_download":
                await combine_and_send_results(websocket, session, agent)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error handling WebSocket connection: {e}")
        logger.error(traceback.format_exc())


async def handle_user_message(websocket: WebSocket, session: Session, agent: Agent, user_message: str,
                              images_uploaded: list):
    response_handler = ResponseHandler(agent=agent, session=session)

    async for response in response_handler.start_agent_loop(
            user_message=user_message, images_uploaded=images_uploaded
    ):
        await websocket.send_json(response)


async def combine_and_send_results(websocket: WebSocket, session: Session, agent: Agent):
    response_handler = ResponseHandler(agent=agent, session=session)

    async for response in response_handler.combine_and_send_results():
        await websocket.send_json(response)
