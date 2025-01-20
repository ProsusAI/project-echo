import logging
from enum import Enum
from typing import Optional, List

import tiktoken

logger = logging.getLogger(__name__)

class OpenAIMessageType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION_CALL = "function_call"
    FUNCTION_CALL_RESPONSE = "function"


def calculate_openai_model_max_tokens(
        openai_messages_tokens_length: int, openai_model_max_tokens: int
) -> int:
    """
    Calculate the openai model max tokens
    :param openai_messages_tokens_length: the openai messages tokens length
    :param openai_model_max_tokens: the openai model max tokens
    :return: the openai model max tokens to use in order not to exceed the maximum tokens limit
    """
    max_tokens = openai_model_max_tokens - openai_messages_tokens_length
    max_tokens = min(max_tokens, 4096)
    return max_tokens


def get_last_openai_message_type(openai_messages: list) -> Optional[OpenAIMessageType]:
    last_message = openai_messages[-1]
    logger.info(f"Last message: {last_message}")
    role = last_message.get("role")
    logger.info(f"Role: {role}")
    if role == "user":
        return OpenAIMessageType.USER
    elif role == "assistant":
        if "function_call" in last_message:
            return OpenAIMessageType.FUNCTION_CALL
        else:
            return OpenAIMessageType.ASSISTANT
    elif role == "function":
        return OpenAIMessageType.FUNCTION_CALL_RESPONSE
    else:
        return None


def filter_openai_messages(openai_messages: list, drop_images:bool = True) -> list:
    filtered_openai_messages = []
    for message in openai_messages:
        if message.get("role") == "user" and not drop_images:
            filtered_openai_messages.append(message)
        elif message.get("role") == "user" and drop_images:
            message_content = message.get("content")
            text_content = ""
            if isinstance(message_content, list):
                for content in message_content:
                    if content.get("type") == "text":
                        text_content += content.get("text", "")
                        filtered_openai_messages.append({"role": "user", "content": text_content})
        elif message.get("role") == "assistant" and "function_call" not in message and message.get("content"):
            filtered_openai_messages.append(message)

    return filtered_openai_messages


def sanitize_triple_backquotes(txt: str):
    return txt.replace("```", r"\`\`\`")


def build_response_from_chunks(chunks: List[str], max_tokens: int) -> str:
    """
    This function builds a response string from a list of text chunks. The response contains as many chunks as possible,
    without exceeding the specified maximum number of tokens. The text is encoded and decoded using a tokenizer for the
    GPT-4 model, and the chunks in the response are enumerated.

    :param chunks: A list of strings representing the text chunks to build the response from.
    :param max_tokens: The maximum number of tokens allowed in the response.

    :return: The resulting response as a string.
    """

    dv_encoder = tiktoken.encoding_for_model("gpt-4o")

    encoded_chunks = [dv_encoder.encode(chunk) for chunk in chunks]

    chunk_lens = [len(encoded_chnk) for encoded_chnk in encoded_chunks]

    # If the total number of tokens in all chunks is less than max_tokens,
    # the response contains all chunks
    if sum(chunk_lens) < max_tokens:
        response = [f"Chunk: {idx + 1}: {text}" for idx, text in enumerate(chunks)]
        response = "\n".join(response)

    # If the last chunk alone exceeds max_tokens,
    # the response contains the beginning of the last chunk up to max_tokens
    elif chunk_lens[-1] > max_tokens:
        response_encoded = encoded_chunks[-1][:max_tokens]
        response = dv_encoder.decode(response_encoded)
        response = f"Chunk: {len(chunks)}: {response}"

    # If the total number of tokens exceeds max_tokens,
    # the response contains as many chunks from the end of the list as possible, without exceeding max_tokens
    else:
        response = []
        response_len = 0
        for idx, chunk in enumerate(chunks[::-1]):
            chunk_len = chunk_lens[-idx - 1]
            if response_len + chunk_len < max_tokens:
                response.append(f"Chunk: {len(chunks) - idx}: {chunk}")
                response_len += chunk_len
            else:
                break
        response = "\n".join(response[::-1])

    return response