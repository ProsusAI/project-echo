import logging
import uuid
from typing import List
from app.core.tool_executor.tools.long_text.long_text_handling_task import LongTextHandlingTask
from app.utils import long_text_handler
from app.utils.common_utils import split_long_text, perform_online_qa
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QuestionAnsweringTask(LongTextHandlingTask):
    async def execute(self):
        try:
            tool_call_id = str(uuid.uuid4())
            questions = self.tool_args.get("questions", [])

            if self.user_uploaded_file is None:
                async for update in self.handle_file_not_found():
                    yield update
                return

            yield {
                "tool_call_id": tool_call_id,
                "message_type": "tool_progress",
                "content": f"Answering {len(questions)} questions based on the content of {self.input_filename}...",
                "icon": "mdi:file-question"
            }

            file_content = self._read_file_content_from_s3()
            response_text = await self._use_vector_search(file_content, questions)

            logger.info(f"Response text: {response_text}")

            if len(response_text) > 0:
                qa_file_url = await self._upload_output_text_to_s3_and_create_url(response_text, self.output_filename)
                response_text = f"Questions and answers: {response_text}\n\nQuestions and answers file url to be shared with user: {qa_file_url}"

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=response_text)

            yield {
                "tool_call_id": tool_call_id,
                "message_type": "tool_progress",
                "content": f"{len(questions)} Questions answered for {self.input_filename}",
                "icon": "mdi:file-check"
            }
        except Exception as e:
            async for update in self.handle_exception(e, "question answering"):
                yield update

    async def _use_vector_search(self, file_content: str, questions: List[str]) -> str:
        text_chunks = split_long_text(long_text=file_content, chnk_size=1024)
        response_text = await perform_online_qa(
            questions=questions,
            text_docs=text_chunks
        )
        return response_text
