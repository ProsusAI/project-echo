import logging
from typing import Union, List

import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter

from app.utils.openai_utils import build_response_from_chunks, sanitize_triple_backquotes
from litellm import acompletion
logger = logging.getLogger(__name__)


class AbstractChunkingStrategy:
    def __init__(self, chunk_size: int, chunk_overlap: int = 0):
        """
        Abstract class for chunking strategy. Each chunking strategy should inherit this.

        :param chunk_size: The maximum size for each chunk.
        :param chunk_overlap: Amount of overlap between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def __call__(self, long_text: Union[List, List[str]]) -> List[str]:
        """
        Calls the chunking strategy.

        :param long_text: Long text either as `str` or `list[str]` which will be chunked.
        :return: list of chunks, chunked according to the implemented strategy.
        """
        raise NotImplementedError


class AbstractCombiningStrategy:
    def __init__(
            self, conversation_role_text_placeholder: str, users_metadata_placeholder: str,
    ):
        """
        Abstract class for combining strategy. Each combining strategy should inherit this.

        :param conversation_role_text_placeholder: The conversation role text.
        :param users_metadata_placeholder: The user info.
        """
        self.conversation_role_text_placeholder = conversation_role_text_placeholder
        self.users_metadata_placeholder = users_metadata_placeholder

    async def __call__(
            self, query: str, long_text_chunks: List[str], conversation_chunks: List[str] = None,
            stop: Union[str, List] = None
    ) -> str:
        """
        Calls the combining strategy.

        :param query: The user message or question to answer using the long_text.
        :param long_text_chunks: The list of chunks obtained from chunking a long text document.
        :param conversation_chunks: The list of chunks obtained from chunking the conversation history.
        :param stop: The stop token(s) for generation.
        :return: An answer to the `query` using the `long_text_chunks`.
        """
        raise NotImplementedError


class RecursiveChunkingStrategy(AbstractChunkingStrategy):
    def __init__(self, chunk_size: int, chunk_overlap: int = 0, model_name: str = "gpt-4o", merge=True):
        """
        Recursive chunking strategy based on Langchain's `RecursiveCharacterTextSplitter`.

        :param chunk_size: The maximum size for each chunk.
        :param chunk_overlap: Amount of overlap between consecutive chunks.
        :param model_name: The `tiktoken` encoder associated with this model used to count length.
        :param merge: Remerge chunks that can still fit more tokens.
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.model_name = model_name
        self.merge = merge
        self._text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name=self.model_name,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    async def __call__(self, long_text: Union[str, List[str]]) -> List[str]:
        # If given long text is a string, then directly chunk it.
        if isinstance(long_text, str):
            chunks = self._text_splitter.split_text(long_text)
        else:
            # If given long text is a list, then chunk each item independently.
            chunks = []
            for text in long_text:
                local_chunks = self._text_splitter.split_text(text)
                chunks.extend(local_chunks)

        if not self.merge:
            return chunks

        merged_chunks = []
        num_tokens = lambda x: len(tiktoken.encoding_for_model("gpt-4o").encode(x))
        for chunk in chunks:
            while merged_chunks and num_tokens(merged_chunks[-1] + chunk) <= self.chunk_size:
                chunk = merged_chunks.pop() + chunk
            merged_chunks.append(chunk)

        return merged_chunks


class TokenTextChunkingStrategy(AbstractChunkingStrategy):
    def __init__(self, chunk_size: int, chunk_overlap: int = 0, model_name: str = "gpt-4o"):
        """
        Token splitting based on Langchain's `TokenTextSplitter`.

        :param chunk_size: The maximum size for each chunk.
        :param chunk_overlap: Amount of overlap between consecutive chunks.
        :param model_name: The `tiktoken` encoder associated with this model used to count length.
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.model_name = model_name
        self._text_splitter = TokenTextSplitter(
            model_name=self.model_name,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    async def __call__(self, long_text: Union[str, List[str]]) -> List[str]:
        # If given long text is a string, then directly chunk it.
        if isinstance(long_text, str):
            return self._text_splitter.split_text(long_text)

        # If given long text is a list, then chunk each item independently into different chunks.
        chunks = []
        for text in long_text:
            local_chunks = self._text_splitter.split_text(text)
            chunks.extend(local_chunks)
        return chunks


class LinearCombiningStrategy(AbstractCombiningStrategy):
    def __init__(
            self, model_names: Union[List[str], str], action_prompt_template: str,
            conversation_role_text_placeholder: str, users_metadata_placeholder: str,
    ):
        """
        This strategy will process given chunks sequentially, and concatenate the result at the end.

        :param model_names: The list of models available for response generation.
        :param action_prompt_template: The action prompt for response generation.
        :param conversation_role_text_placeholder: The conversation role text.
        :param users_metadata_placeholder: The user info.
        """
        super().__init__(
            conversation_role_text_placeholder, users_metadata_placeholder
        )
        self.model_names = model_names
        self.action_prompt_template = action_prompt_template

    async def __call__(
            self, query: str, long_text_chunks: List[str], conversation_chunks: List[str] = None,
            stop: Union[str, List] = None
    ) -> str:

        if not conversation_chunks:
            conversation_chunks = []

        all_chunks = [("", c) for c in conversation_chunks] + [(c, "") for c in long_text_chunks]
        chunk_responses = []

        response_so_far = "Has not started yet."
        for index, (long_text_chunk, conversation_chunk) in enumerate(all_chunks, start=1):
            prompt = self.action_prompt_template.format(
                current_chunk=index,
                total_chunks=len(all_chunks),
                input_text=long_text_chunk,
                conversation=conversation_chunk,
                user_request=query,
                response_so_far=response_so_far,
                conversation_role_text_placeholder=self.conversation_role_text_placeholder,
                users_metadata_placeholder=self.users_metadata_placeholder
            )

            openai_response = await acompletion(
                model=self.model_names[0],
                fallbacks=self.model_names[1:],
                messages=[{
                    "role": "system",
                    "content": prompt
                },
                    {
                        "role": "user",
                        "content": f"Your response for chunk {index}:"
                    }],
            )

            response = openai_response["choices"][0]["message"]["content"]

            if response.strip() == "[PASS]":
                continue

            chunk_responses.append(response)
            response_so_far = build_response_from_chunks(chunk_responses, 1000)

        return "\n".join(chunk_responses)


class MapReduceCombiningStrategy(AbstractCombiningStrategy):
    def __init__(
            self, short_context_models: List[str], long_context_models: List[str],
            action_prompt_template: str, combination_prompt_template: str,
            conversation_role_text_placeholder: str, users_metadata_placeholder: str, short_context_size: int = 8000,
            long_context_size: int = 32000, max_depth: int = 5
    ):
        """
        This recursive strategy at each depth will process given chunks sequentially,
        and combine the results at the end. The results are re-chunked and passed on to next depth.

        :param short_context_models: The list of short context models available for response generation.
        :param long_context_models: The list of long context models available for response generation.
        :param action_prompt_template: The action prompt for response generation.
        :param combination_prompt_template: The combination prompt for combining responses of chunks. 
        :param conversation_role_text_placeholder: The conversation role text.
        :param users_metadata_placeholder: The user info.
        :param max_depth: Max recursive depth.
        """
        super().__init__(
            conversation_role_text_placeholder, users_metadata_placeholder,
        )
        self.short_context_models = short_context_models
        self.long_context_models = long_context_models
        self.action_prompt_template = action_prompt_template
        self.combination_prompt_template = combination_prompt_template
        self.short_context_size = short_context_size
        self.long_context_size = long_context_size
        self.max_depth = max_depth

        self._chunking_strategy = RecursiveChunkingStrategy(2000, 200)
        self._combining_strategy = LinearCombiningStrategy(
            short_context_models, action_prompt_template, conversation_role_text_placeholder,
            users_metadata_placeholder
        )
        self._encoder = tiktoken.encoding_for_model("gpt-4o")
        self._min_reserved_tokens = 1000
        self._max_tokens_for_short_ctx = int(0.75 * self.short_context_size)
        self._max_tokens_for_long_ctx = int(0.75 * self.long_context_size)

    async def _recurse(
            self, query: str, long_text_chunks: List[str], conversation_chunks: List[str] = None,
            stop: Union[str, List] = None, depth: int = 0
    ):

        if not conversation_chunks:
            conversation_chunks = []

        if depth > self.max_depth:
            raise Exception(f"Could not compress information after {depth} iterations")

        response = self._combining_strategy(query, long_text_chunks, conversation_chunks, stop)
        reserved_response_tokens = max(
            len(self._encoder.encode(response)), self._min_reserved_tokens
        )

        prompt = self.combination_prompt_template.format(
            all_responses=sanitize_triple_backquotes(response),
            user_request=sanitize_triple_backquotes(query),
            users_metadata_placeholder=sanitize_triple_backquotes(self.users_metadata_placeholder)
        )
        prompt_tokens = len(self._encoder.encode(prompt))

        total_prompt_length = reserved_response_tokens + prompt_tokens
        # If number of tokens is larger than context size for the largest models,
        # we need another iteration of map-reduce.
        if total_prompt_length > self._max_tokens_for_long_ctx:
            new_request_chunks = self._chunking_strategy(response)
            return self._recurse(query, new_request_chunks, conversation_chunks, stop, depth + 1)
        # If number of tokens is within the context size for largest models,
        # we can use long context models in this iteration.
        elif self._max_tokens_for_short_ctx < total_prompt_length < self._max_tokens_for_long_ctx:
            model_names = self.long_context_models
        # Number of tokens is small enough to fit into context size of short models.
        else:
            model_names = self.short_context_models

        openai_response = await acompletion(
            model=model_names[0],
            fallbacks=model_names[1:],
            messages=[{
                "role": "system",
                "content": prompt
            }],
        )

        response = openai_response["choices"][0]["message"]["content"]

        return response

    async def __call__(
            self, query: str, long_text_chunks: List[str], conversation_chunks: List[str] = [],
            stop: Union[str, List] = None
    ) -> str:
        return await self._recurse(query, long_text_chunks, conversation_chunks, stop, 0)


class LongTextHandler:
    def __init__(
            self,
            chunking_strategy: AbstractChunkingStrategy = None,
            combining_strategy: AbstractCombiningStrategy = None,
    ):
        """
        The wrapper class responsible for long-text handling. This is achieved by
        invoking the provided chunking and combining strategies.

        :param chunking_strategy: Strategy to use for chunking input long text.
        :param combining_strategy: Strategy to use for combining chunks into response.
        """
        self.chunking_strategy = chunking_strategy
        self.combining_strategy = combining_strategy

    async def __call__(
            self,
            query: str,
            long_text: Union[str, List[str]],
            conversation: Union[str, List[str]] = None,
            stop: str = None,
    ) -> str:
        """
        Invoke the long text handling.

        :param query: The user message or question to answer using the long_text.
        :param long_text: Long text either as `str` or `list[str]` which will be chunked.
        :param conversation: The user conversation history.
        :param stop: The stop token(s) for generation.
        :param debug: If set, returns a dictionary for debugging purposes.
        :return:
            An answer to the `query` using the `long_text` and `conversation`.
            (Optional) Debug info containing `long_text_n_chunks`, `is_long_text`.
        """
        if not conversation:
            conversation = []

        long_text_chunks = self.chunking_strategy(long_text)
        conversation_chunks = self.chunking_strategy(conversation)
        response = self.combining_strategy(query, long_text_chunks, conversation_chunks, stop)

        _total_chunks = len(long_text_chunks) + len(conversation_chunks)

        return response
