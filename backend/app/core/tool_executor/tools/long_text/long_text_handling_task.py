from abc import abstractmethod
import logging

from app.models.session_model import Session
from app.core.tool_executor.tools import AgentTool
from app.utils.aws_utils import download_file_as_bytes_from_s3
from app.utils.aws_utils import S3_BUCKET_NAME, extract_text_from_bytes
from app.utils.common_utils import extract_file_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LongTextHandlingTask(AgentTool):
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
        self.tool_args["filename"] = extract_file_name(self.tool_args["filename"])
        self.input_filename = self.tool_args["filename"]
        input_filename_wo_ext = self.input_filename.split(".")[0]
        self.output_filename = extract_file_name(
            self.tool_args.get("output_filename", f"{input_filename_wo_ext}_output.md"))
        self.user_uploaded_file = self._find_uploaded_file(self.input_filename)

    def _read_file_content_from_s3(self) -> str:
        """
        Reads the file content from s3
        :return: the file content
        """
        if self.user_uploaded_file is None:
            raise ValueError(f"File {self.input_filename} not found in uploaded files.")
        
        print("KEY:", self.user_uploaded_file.s3_key)
        text_file_as_bytes = download_file_as_bytes_from_s3(
            S3_BUCKET_NAME,
            self.user_uploaded_file.s3_key,
        )
        file_type = self.user_uploaded_file.filename.split(".")[-1]
        file_content = extract_text_from_bytes(file_type, text_file_as_bytes)
        return file_content

    @abstractmethod
    async def execute(self):
        pass

    async def handle_file_not_found(self):
        message = f"Sorry, I couldn't find {self.input_filename} in your uploaded files. Please try again."
        self.add_openai_function_response(content=message)
        yield {
            "tool_call_id": self.tool_call_id,
            "message_type": "tool_error",
            "content": message,
            "icon": "mdi:file-alert"
        }

    async def handle_exception(self, e: Exception, task_name: str):
        error_message = f"Error in {task_name}: {str(e)}"
        logger.error(error_message, exc_info=True, extra={"session_id": self.agent_session.id})
        self.add_openai_function_call(arguments=self.tool_args)
        self.add_openai_function_response(content=error_message)
        yield {
            "tool_call_id": self.tool_call_id,
            "message_type": "tool_error",
            "content": error_message,
            "icon": "mdi:file-alert"
        }
