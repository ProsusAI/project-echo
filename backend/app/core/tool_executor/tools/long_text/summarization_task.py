import logging
import traceback
import uuid

from llama_index.core import Response, get_response_synthesizer, Document, GPTTreeIndex, Settings
from llama_index.core.response_synthesizers import ResponseMode

from app.core.tool_executor.tools.long_text.long_text_handling_task import LongTextHandlingTask
from app.utils.common_utils import split_long_text

from app.config import get_settings
from llama_index.llms.openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SummarizationTask(LongTextHandlingTask):
    async def _generate_summary(self, file_content: str, summary_request: str) -> Response:
        """
        Generates a summary of the file content
        :param file_content: the file content
        :param summary_request: the summary request
        :return: the summary
        """
        model_name = "gpt-4o-mini"
        llm = OpenAI(
            model=model_name,
            temperature=0.5,
            api_key=get_settings().openai_api_key,
            fallback_model_list=get_settings().fallback_openai_models,
        )
        Settings.llm = llm
        Settings.chunk_size = 2048
        Settings.context_window = 64000
        response_synthesizer = get_response_synthesizer(
            response_mode=ResponseMode.TREE_SUMMARIZE, use_async=True
        )
        # chunk the document into multiple documents
        text_chunks = split_long_text(long_text=file_content, chnk_size=1024)
        documents = [Document(text=text) for text in text_chunks]
        doc_summary_index = GPTTreeIndex.from_documents(
            documents=documents,
        )
        query_engine = doc_summary_index.as_query_engine(
            response_synthesizer=response_synthesizer,
            use_async=True,
            retriever_mode="all_leaf",
            child_branch_factor=2,
        )
        query_response = await query_engine.aquery(summary_request)
        return query_response

    async def execute(self):
        try:
            tool_call_id = str(uuid.uuid4())
            summary_request = self.tool_args.get(
                "user_summary_request", "Create a detailed summary of this text."
            )

            if self.user_uploaded_file is None:
                async for update in self.handle_file_not_found():
                    yield update
                return

            yield {
                "tool_call_id": tool_call_id,
                "message_type": "tool_progress",
                "content": f"Summarizing the content of {self.input_filename}...",
                "icon": "mdi:file-document-edit-outline"
            }

            file_content = self._read_file_content_from_s3()
            query_response = await self._generate_summary(file_content, summary_request)
            summary_text = query_response.response

            if len(summary_text) > 0:
                summary_file_url = await self._upload_output_text_to_s3_and_create_url(summary_text, self.output_filename)
                summary_text = f"Summary: {summary_text}\n\nSummary file url to be shared with user: {summary_file_url}"

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=summary_text)
            self.add_additional_system_message(content=f"Based on the summary's text, ask and answer 10 to 30 questions to understand the content better using the question and answering task in the file handling tool, answer the questions using the original document and not the summary.")

            yield {
                "tool_call_id": tool_call_id,
                "message_type": "tool_progress",
                "content": f"Summary generated for {self.input_filename}",
                "icon": "mdi:file-document-check"
            }
        except Exception as e:
            async for update in self.handle_exception(e, "summarization"):
                yield update
