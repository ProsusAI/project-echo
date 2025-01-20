from typing import Literal, List, Optional, Dict

from pydantic import Field

from app.models.session_model import Session
from app.schemas.tool_model import ToolInput
from app.core.tool_executor.tools import AgentTool
from app.core.tool_executor.tools.long_text import (
    PrintFileContentTask,
    QuestionAnsweringTask,
    SummarizationTask,
)
import logging
import traceback
import asyncio
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FileHandlingTool(AgentTool):
    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.FileHandling.get_schema(replacements)

    class FileHandling(ToolInput):
        """Handles text and images (via OCR) files by using ones of three possible operations. Summarization, printing out the file content and question answering using a list of 5-20 provided questions"""
        filename: str = Field(...,
                              description="The name of the text or image file to handle from the user uploaded files")
        task_type: Literal[
            "summarization",
            "question_answering",
            "printing_file_content",
        ] = Field(
            ...,
            description="The type of task to perform on the text file. It can be one of the following: summarization, question_answering and printing_file_content",
        )
        output_filename: str = Field(None,
                                     description="The name of the output markdown file (.md) that will be generated for summarization and question answering tasks.")
        questions: List[str] = Field([],
                                     description="In the question_answering task type, pass the questions that will be used to find the answers in the text file then it will return one answer for each question. You must provide at least 5 questions and it can be up to 30 questions")
        user_summary_request: str = Field("Create up to 10 paragraph summary of the text and include a list of all the facts mentioned in the text.",
                                          description="An LLM prompt that will be used to generate the summary. Always state the number of paragraphs required in the summary request. Minimum is 10 paragraphs and maximum is 20 paragraphs.")

    def __init__(
            self,
            tool_name: str,
            tool_args: dict,
            tool_call_id: str,
            agent_session: Session,
            workflow: str,
    ):
        super().__init__(
            tool_name,
            tool_args,
            tool_call_id,
            agent_session,
            workflow
        )
        self.long_text_handling_tasks = {
            "summarization": SummarizationTask,
            "question_answering": QuestionAnsweringTask,
            "printing_file_content": PrintFileContentTask,
        }

    async def execute(self):
        long_text_file_handling = self.FileHandling(**self.tool_args)
        try:
            task_class = self.long_text_handling_tasks.get(long_text_file_handling.task_type)
            if task_class is None:
                error_message = f"Invalid task type: {long_text_file_handling.task_type}"
                yield {
                    "tool_call_id": self.tool_call_id,
                    "message_type": "tool_error",
                    "content": error_message,
                    "icon": "mdi:file-alert"
                }
                return

            task = task_class(
                self.tool_name,
                self.tool_args,
                self.tool_call_id,
                self.agent_session,
                self.workflow,
            )
            task_coroutine = task.execute()
            task_obj = asyncio.create_task(anext(task_coroutine))
            
            while not task_obj.done():
                try:
                    result = await asyncio.wait_for(asyncio.shield(task_obj), timeout=0.1)
                    yield result
                except asyncio.TimeoutError:
                    await asyncio.sleep(0.1)
                
            # Yield any remaining results
            async for update in task_coroutine:
                yield update
                
        except Exception as e:
            logger.error(f"Error executing long text handling task: {e}")
            logger.error(traceback.format_exc())
            self.add_openai_function_call(self.tool_args)
            self.add_openai_function_response(content=f"Error occurred while executing the {long_text_file_handling.task_type} task: {e}")
            yield {
                "tool_call_id": self.tool_call_id,
                "message_type": "tool_error",
                "content": f"Error occurred while executing the {long_text_file_handling.task_type} task: {e}",
                "icon": "mdi:file-alert"
            }
