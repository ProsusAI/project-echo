import io
import json
import logging
from datetime import datetime
from typing import List

import litellm

from app.config import get_settings
from app.core.llm_integration.message_preparation import MessagePreparer
from app.core.tool_executor.tool_executor import ToolExecutor
from app.models.session_model import Session, MessageType, SessionStatus
from app.utils.audio_utils import download_audio_segments, stitch_audio_segments, create_srt_content, zip_audio_and_srt
from app.utils.aws_utils import upload_bytes_to_s3_and_create_urls
from app.utils.openai_utils import calculate_openai_model_max_tokens, OpenAIMessageType, get_last_openai_message_type, \
    filter_openai_messages

logger = logging.getLogger("response_handling")


class ResponseHandler:
    def __init__(self, agent, session: Session):
        self.agent = agent
        self.session = session
        self.tool_executor = ToolExecutor(agent=agent)
        self.finish_reason = None
        self.is_streaming = True

    async def stream_and_handle_response(self, max_tokens: int, openai_messages: List[dict], is_a_new_call: bool):
        if not self.agent.models:
            raise ValueError("Agent models are not set")

        tools = [{"type": "function", "function": function} for function in self.agent.tools_schema()]
        tool_call_accumulator = ""
        tool_call_name = None
        bot_response = ""
        model_parameters = {
            "temperature": 1.0,
            "top_p": 1.0,
            "max_tokens": max_tokens,
            "stream": self.is_streaming,
            "tool_choice": "auto",
        }
        last_openai_message_type = get_last_openai_message_type(self.session.openai_messages)

        async def on_new_token(token: str):
            if not self.session.messages or self.session.messages[
                -1].message_type != MessageType.BOT or is_a_new_call or last_openai_message_type in [
                OpenAIMessageType.FUNCTION_CALL_RESPONSE,
                OpenAIMessageType.SYSTEM]:
                yield {"message_type": "new_message", "content": token}
            else:
                self.session.messages[-1].text += token
                yield {"message_type": "update_message", "content": token}

        stream = await litellm.acompletion(
            model=self.agent.models[0],
            messages=openai_messages,
            fallbacks=get_settings().fallback_openai_models,
            tools=tools,
            max_retries=2,
            **model_parameters,
        )

        tools_to_call = []
        async for chunk in stream:
            self.finish_reason = chunk.choices[0].finish_reason
            chunk_content = chunk.choices[0].delta.content
            chunk_tool_calls = chunk.choices[0].delta.tool_calls

            if chunk_content:
                bot_response += chunk_content
                async for token_response in on_new_token(chunk_content):
                    yield token_response
                    is_a_new_call = False

            if chunk_tool_calls:
                for tool_call in chunk_tool_calls:
                    if tool_call.id:
                        tool_call_name = tool_call.function.name if tool_call.function else None

                    tool_call_accumulator += tool_call.function.arguments if tool_call.function and tool_call.function.arguments else ""

                    try:
                        func_args = json.loads(tool_call_accumulator)
                        tools_to_call.append({
                            "tool_name": tool_call_name,
                            "tool_args": func_args,
                        })
                        tool_call_accumulator = ""
                    except json.JSONDecodeError:
                        pass

        if bot_response:
            self.session.openai_messages.append({"role": "assistant", "content": bot_response})
            self.session.add_message(MessageType.BOT, bot_response)

        async for tool_update in self.tool_executor.execute_tools_concurrently(tools_to_call, self.session, self.agent.workflow):
            if tool_update.get("message_type") == "validation_error":
                error_message = tool_update["content"]
                tool_name = tool_update["tool_name"]
                system_message = (
                    f"There was a validation error when trying to execute the {tool_name} tool. "
                    f"Error details: {error_message}\n"
                    f"Please review the input parameters for this tool and try to correct them. "
                    f"If you're unsure how to proceed, ask the user for clarification or suggest an alternative approach."
                )
                self.session.openai_messages.append({
                    "role": "system",
                    "content": system_message
                })
            yield tool_update

    async def handle_exception(self, error_message: str, e: Exception):
        logger.exception(f"Error executing the agent: {e}")
        self.session.openai_messages.append(
            {"role": "assistant", "content": error_message}
        )
        self.session.status = SessionStatus.FAILED
        self.session.save()

    async def _recommend_follow_up_responses(self) -> List[str]:
        main_prompt_system_message = self.session.openai_messages[0]

        system_prompt = (
            """
            You are tasked with recommending possible responses that the user can respond with to continue the conversation, get more information about the current topic or get more value out of the conversation by pretending to be the user.
            If no responses are possible because of the lack of conversation history, return an empty list.
            A response should be a short sentence so it can fit on a small button in a chat interface.\n"""
            "The user is communicating with an AI assistant that has the following system prompt and guidelines: {main_prompt_system_message}\n You need to generate suitable responses for the user based on the assistant's use case and the conversation history.\n"
            """Return 2 to 3 responses as a valid python dict (Similar to the example below). Don't return any other information except the JSON with the possible responses as options for the options based on the context, last message.
            Expected JSON format: {"responses": ["string", "string"]}
            
            Valid Examples when the user's messages are in English:
            # Example 1
            {
                "responses": [
                    "Create a supporting character called `Sally` who is a detective",
                    "Set a suitable title and create 3 characters for the story",
                    "Suggest a good title based on the discussion"
                ]
            }
            
            # Example 2
            {
                "responses": [
                    "Create scene 2 of the podcast.",
                    "Search the web for `Home Robots` and use the knowledge to create a scene 2.",
                    "Add a plot twist in the next scene."
                ]
            }
            
            Follow the following guidelines when generating the responses:
            - Proposed responses should be relevant to the conversation and offers possible concise responses for the user to continue the conversation.
            - Keep the responses short and concise
            - Never propose responses involving images, videos, urls, or any other media.
            - The responses should only suggest using tools that the assistant has access to (the tools that don't require a file or a URL as input).
            - Focus on responses that will make the conversation more engaging and interactive so the user doesn't see the need to type a message to continue the conversation.
            - Avoid responses that are too generic or not relevant to the conversation.
            - Avoid responses that are too specific or too personal.
            - Avoid responses that are too long or complex.
            - Avoid responses that are too similar to the previous messages.
            - Avoid responses that are too similar to the examples provided in the guidelines.
            - Avoid responses that suggest listening to audio, downloading files or other capabilities that you don't have access to.
            """
        )

        # filter and get the last 2 messages
        filtered_openai_messages = filter_openai_messages(self.session.openai_messages)[-2:]
        logging.info(
            f"Filtered openai messages for follow up responses generation: {filtered_openai_messages}, len: {len(filtered_openai_messages)}")
        user_prompt = f"Return the follow-up responses in valid JSON based on the recent conversation history. Recent conversation history (up to the last 2 messages between user and AI assistant): {str(filtered_openai_messages)}"

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        model = "gpt-4o-mini"
        model_parameters = {
            "temperature": 0.5,
            "top_p": 1.0,
            "max_tokens": 4096,
            "stream": False,
        }
        follow_up_questions_examples = []
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                fallbacks=get_settings().fallback_openai_models,
                response_format={"type": "json_object"},
                max_retries=2,
                **model_parameters,
            )
            json_response = json.loads(response.choices[0].message.content)
            if "responses" in json_response:
                follow_up_questions_examples = json_response["responses"]

            follow_up_questions_examples = [q for q in follow_up_questions_examples if len(q) <= 300]
        except Exception as e:
            logging.exception(f"Error getting the follow-up questions example: {e}",
                              extra={
                                  "demo_name": self.session.demo_name,
                                  "agent_session_id": self.session.id,
                              })
            raise e

        response = follow_up_questions_examples[:4]
        return response

    async def start_agent_loop(self, user_message: str, images_uploaded: List[str]):
        is_a_new_user_message = True

        yield {"message_type": "loading_indicator", "status": "start"}

        try:
            while self.finish_reason != "stop":
                is_a_new_call = True
                preparer = MessagePreparer()
                openai_messages, openai_messages_tokens_length = preparer.prepare_messages(
                    agent=self.agent,
                    agent_session=self.session,
                    user_message=user_message,
                    images_uploaded=images_uploaded,
                    is_a_new_user_message=is_a_new_user_message,
                    openai_defined_functions=self.agent.tools_schema(),
                    openai_model_max_tokens=self.agent.llm_max_tokens,
                    custom_user_instructions=None
                )

                is_a_new_user_message = False

                max_tokens = calculate_openai_model_max_tokens(
                    openai_messages_tokens_length, self.agent.llm_max_tokens
                )

                async for response in self.stream_and_handle_response(max_tokens, openai_messages, is_a_new_call):
                    yield response

                self.session.session_last_update_datetime = datetime.utcnow()
                self.session.save()
        except TypeError as e:
            error_response = "I am sorry, the request failed due to a temporary issue. Please try again later."
            await self.handle_exception(error_message=error_response, e=e)
        except Exception as e:
            error_response = "I am sorry, I encountered an error while executing your request. Please try again."
            await self.handle_exception(error_message=error_response, e=e)
        finally:
            self.session.status = SessionStatus.WAITING_FOR_USER_INPUT
            self.session.session_last_update_datetime = datetime.utcnow()
            self.session.save()

        yield {"message_type": "loading_indicator", "status": "stop"}
        follow_up_responses = await self._recommend_follow_up_responses()
        if follow_up_responses:
            yield {"message_type": "follow_up_responses", "content": follow_up_responses}

    async def combine_and_send_results(self):
        sorted_audio_segments = sorted(self.session.audio_segments, key=lambda x: x["segment_index"])
        audio_segments = await download_audio_segments(sorted_audio_segments)
        combined_audio = stitch_audio_segments(audio_segments)
        srt_content = create_srt_content(sorted_audio_segments)
        audio_data = io.BytesIO()
        combined_audio.export(audio_data, format="mp3")
        audio_data.seek(0)

        if self.session.content_title:
            title = self.session.content_title.replace(" ", "_").replace(":", "").replace("?", "").replace("!",
                                                                                                           "").replace(
                "'", "").replace('"', "").lower().strip()
        else:
            title = f"project_echo_{self.session.id}_{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}"

        zip_data = zip_audio_and_srt(audio_data.read(), srt_content)
        file_presigned_url = await upload_bytes_to_s3_and_create_urls(
            file_bytes=zip_data,
            demo_name=self.session.demo_name,
            session_id=self.session.id,
            output_filename=f"{title}.zip"
        )
        short_url = file_presigned_url.replace("/minio:", "/localhost:")

        self.session.openai_messages.append(
            {
                "role": "system",
                "content": f"Inform the user that the audio and subtitle files are ready for download. Provide the user with the following link: {short_url}. Create two new lines before your message to separate it from the previous conversation."
            }
        )

        preparer = MessagePreparer()
        openai_messages, openai_messages_tokens_length = preparer.prepare_messages(
            agent=self.agent,
            agent_session=self.session,
            user_message="",
            images_uploaded=[],
            is_a_new_user_message=False,
            openai_defined_functions=self.agent.tools_schema(),
            openai_model_max_tokens=self.agent.llm_max_tokens,
            custom_user_instructions=None
        )

        max_tokens = calculate_openai_model_max_tokens(
            openai_messages_tokens_length, self.agent.llm_max_tokens
        )

        async for response in self.stream_and_handle_response(max_tokens, openai_messages, True):
            yield response

        self.session.session_last_update_datetime = datetime.utcnow()
        self.session.save()

        yield {"message_type": "loading_indicator", "status": "stop"}
