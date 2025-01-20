import logging
import base64
import requests
from typing import List, Dict, Optional, Tuple, Any

from litellm.utils import token_counter

from app.core.agents import Agent
from app.models.session_model import Session
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger("message_preparation")

MAX_TOKENS_COMPLETION_THRESHOLD = 0.5
SYSTEM_ROLE = "system"
USER_ROLE = "user"


class MessagePreparer:
    def prepare_messages(
            self,
            agent: Agent,
            agent_session: Session,
            user_message: str,
            images_uploaded: List[str],
            is_a_new_user_message: bool,
            openai_defined_functions: List[Dict[str, Any]],
            openai_model_max_tokens: int,
            custom_user_instructions: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Prepare messages for OpenAI API call.
        :param agent: The agent object
        :param agent_session: The current session
        :param user_message: The user's message
        :param images_uploaded: List of uploaded image URLs
        :param is_a_new_user_message: Whether this is a new user message
        :param openai_defined_functions: OpenAI functions
        :param openai_model_max_tokens: Maximum tokens for the model
        :param custom_user_instructions: Custom instructions for the user
        :return: Prepared messages and token count
        """
        try:
            if not user_message and not images_uploaded and not agent_session.openai_messages:
                logger.error("No user message or images uploaded provided.")
                raise MessagePreparationError("No user message or images uploaded provided.")

            prompt_builder = PromptBuilder(
                agent=agent,
                agent_session=agent_session,
                custom_user_instructions=custom_user_instructions,
            )
            system_message_content = prompt_builder.build()
            system_message = {
                "role": "system",
                "content": system_message_content,
            }

            # Update the session with the system message if it was not added before
            if len(agent_session.openai_messages) == 0:
                agent_session.openai_messages.append(system_message)
            else:
                agent_session.openai_messages[0] = system_message

            conversation_history = self._get_conversation_history(agent_session)
            user_message = user_message if is_a_new_user_message else None
            images_urls = self._prepare_image_urls(images_uploaded)
            user_message = self._prepare_user_message(user_message, images_urls)

            openai_messages, openai_messages_tokens_length, openai_user_message = self._prepare_messages(
                system_message=system_message,
                user_message=user_message,
                history=conversation_history,
                openai_functions=openai_defined_functions,
                model_max_tokens=openai_model_max_tokens,
                model=agent.models[0],
            )

            # Add the user message to the session if it was not added before
            if openai_user_message:
                agent_session.openai_messages.append(openai_user_message)
            elif not agent_session.openai_messages:
                logger.error("User message is missing and there are no messages in the session")
                agent_session.openai_messages = openai_messages

            return openai_messages, openai_messages_tokens_length

        except Exception as e:
            logger.error(f"Error preparing messages: {e}")
            raise MessagePreparationError(f"Failed to prepare messages: {str(e)}")

    def _prepare_messages(
            self,
            system_message: Dict[str, Any],
            user_message: Dict[str, Any],
            history: List[Dict[str, Any]],
            openai_functions: Optional[List[Dict[str, Any]]] = None,
            model_max_tokens: int = 128000,
            model: str = "gpt-4o",
    ) -> Tuple[List[Dict[str, Any]], int, Optional[Dict[str, Any]]]:
        """
        Manages the messages for OpenAI to ensure that the number of tokens in the prompt does not exceed the model max tokens.
        :param system_message: the system message
        :param user_message: the user message
        :param images_urls: the images urls to send (openai format)
        :param history: the conversation history with PlusOne
        :param openai_functions: the openai functions
        :param model_max_tokens: the max tokens for the model
        :param model: the model to use
        :return: the prepared OpenAI messages and number of tokens
        """
        openai_messages = history + ([user_message] if user_message else [])

        tools = [{"type": "function", "function": function} for function in openai_functions]

        system_and_tools_tokens_count = token_counter(
            model=model,
            messages=[system_message],
            tools=tools,
        )
        prompt_tokens_count = token_counter(
            model=model,
            messages=openai_messages,
        )

        if self._should_crop_history(system_and_tools_tokens_count, prompt_tokens_count, model_max_tokens):
            openai_messages = self._crop_history(
                history=history,
                user_message=user_message,
                prompt_tokens_count=prompt_tokens_count,
                model_max_tokens=model_max_tokens,
                model=model,
            )
            prompt_tokens_count = token_counter(
                model=model,
                messages=openai_messages,
            )
            logger.info(f"History cropped to {len(openai_messages)} messages. New prompt tokens count: {prompt_tokens_count}")

        total_tokens = system_and_tools_tokens_count + prompt_tokens_count
        logger.info(f"Total tokens: {total_tokens}")
        openai_messages = [system_message] + openai_messages

        return openai_messages, total_tokens, user_message

    def _prepare_user_message(
            self, user_message: Optional[str], images_urls: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not images_urls and not user_message:
            return None

        content = []
        if user_message:
            content.append({"type": "text", "text": user_message})
        content.extend(images_urls)

        return {"role": USER_ROLE, "content": content}

    def _should_crop_history(
            self, system_tokens: int, prompt_tokens: int, model_max_tokens: int
    ) -> bool:
        total_tokens = system_tokens + prompt_tokens
        return total_tokens / model_max_tokens > MAX_TOKENS_COMPLETION_THRESHOLD

    def _crop_history(
            self,
            history: List[Dict[str, Any]],
            user_message: Optional[Dict[str, Any]],
            prompt_tokens_count: int,
            model_max_tokens: int,
            model: str,
    ) -> List[Dict[str, Any]]:
        user_message_tokens_count = token_counter(messages=[user_message], model=model) if user_message else 0
        history_ratio = max(
            0.0,
            MAX_TOKENS_COMPLETION_THRESHOLD
            - (user_message_tokens_count / prompt_tokens_count) if prompt_tokens_count else 0,
        )
        max_history_tokens = int(model_max_tokens * history_ratio)
        cropped_history = self._filter_messages_by_token_limit(
            messages=history, token_limit=max_history_tokens, model=model
        )
        return cropped_history + ([user_message] if user_message else [])

    @staticmethod
    def _get_conversation_history(agent_session: Session) -> List[Dict[str, Any]]:
        return agent_session.openai_messages[1:] if agent_session.openai_messages else []

    @staticmethod
    def _prepare_image_urls(images_uploaded: List[str]) -> List[Dict[str, Any]]:

        # download the images and turn into base64
        new_base64_images = []
        for image_url in images_uploaded:
            docker_url = image_url.replace("localhost", "minio")
            image_data = requests.get(docker_url).content
            base64_image = base64.b64encode(image_data).decode("utf-8")
            new_base64_images.append(base64_image)

        return [
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{image_base64}" if not image_base64.startswith("data:image") else image_base64,
                "detail": "low"
            }}
            for image_base64 in new_base64_images
        ]

    @staticmethod
    def _filter_messages_by_token_limit(messages: list, token_limit: int, model: str) -> List:
        """
        Filters a list of historical messages to return the last N messages that don't exceed the given token_limit
        when their tokens are summed.

        :param messages: List of historical messages to filter.
        :param token_limit: The maximum total number of tokens allowed for the returned messages.
        :param model: The model to use to count the tokens.
        :return: A list of filtered messages that meet the token_limit constraint.
        """
        filtered_messages = []
        total_tokens = 0

        for message in reversed(messages):
            n_tokens = token_counter(messages=[message], model=model)
            if total_tokens + n_tokens <= token_limit:
                filtered_messages.append(message)
                total_tokens += n_tokens
            else:
                break

        return list(reversed(filtered_messages))


class MessagePreparationError(Exception):
    """Custom exception for message preparation errors."""
    pass
