import json
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Union

from app.models.session_model import Session, UploadedFile
from app.utils.aws_utils import S3_KEY_TEMPLATE, upload_bytes_to_s3, S3_BUCKET_NAME, create_presigned_url


class AgentTool(ABC):
    def __init__(
            self,
            tool_name: str,
            tool_args: dict,
            tool_call_id: str,
            agent_session: Session,
            workflow: str,
    ):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_call_id = tool_call_id
        self.agent_session = agent_session
        self.workflow = workflow

    @abstractmethod
    async def execute(self) -> None:
        pass

    def _find_uploaded_file(self, filename: str) -> UploadedFile:
        """
        Finds the uploaded file
        :param filename: the file name
        :return: the uploaded file
        """
        for uploaded_file in self.agent_session.user_uploaded_files:
            if uploaded_file.filename == filename:
                return uploaded_file

        raise ValueError(f"Could not find uploaded file with filename {filename}")

    async def stream_update(self, tool_call_id: str, update_type: str, content: Union[str, dict], icon: str = None):
        output = {
            "tool_call_id": tool_call_id,
            "message_type": update_type,
            "content": content
        }

        if icon:
            output["icon"] = icon

        yield output

    def add_openai_function_call(self, arguments: dict, content: str = None):
        """
        Adds a function call to the openai_messages list
        :param arguments: the arguments of the function call
        :param content: the content of the function call
        :return: None
        """
        if self.tool_call_id is not None:
            self.agent_session.openai_messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": self.tool_call_id,
                        "function": {
                            "name": self.tool_name,
                            "arguments": json.dumps(arguments),
                        },
                        "type": "function",
                    }],
                    "content": content,
                }
            )
        else:
            self.agent_session.openai_messages.append(
                {
                    "role": "assistant",
                    "function_call": {
                        "name": self.tool_name,
                        "arguments": json.dumps(arguments),
                    },
                    "content": content,
                }
            )

    def add_openai_function_response(self, content: str = None):
        """
        Adds a function response to the openai_messages list
        :param content: the content of the function response
        :return: None
        """
        if self.tool_call_id is not None:
            self.agent_session.openai_messages.append(
                {
                    "tool_call_id": self.tool_call_id,
                    "role": "tool",
                    "name": self.tool_name,
                    "content": content,
                }
            )
        else:
            self.agent_session.openai_messages.append(
                {
                    "role": "function",
                    "name": self.tool_name,
                    "content": content,
                }
            )

    def _check_system_message_exists(self, content: str, last_n_messages: int = 10) -> bool:
        """
        Checks if a system message with the given content exists in the last n messages
        :param content: the content to check for
        :param last_n_messages: the number of recent messages to check (default: 10)
        :return: True if the message exists, False otherwise
        """
        recent_messages = self.agent_session.openai_messages[-last_n_messages:]
        return any(
            msg.get("role") == "system" and msg.get("content") == content
            for msg in recent_messages
        )

    def add_additional_system_message(self, content: str, check_last_n_messages: int = 10):
        """
        Adds a system message to the agent session if it doesn't exist in recent messages
        :param content: the content of the system message
        :param check_last_n_messages: number of recent messages to check for duplicates (default: 10)
        :return: None
        """
        if not self._check_system_message_exists(content, check_last_n_messages):
            self.agent_session.openai_messages.append(
                {
                    "role": "system",
                    "content": content,
                }
            )

    def _create_uploaded_file_object(
            self,
            filename: str,
            s3_key: str,
            short_url: str = None,
    ) -> UploadedFile:
        """
        Creates an uploaded file object
        :param filename: the file name
        :param s3_key: the s3 key
        :param short_url: the short URL
        :return: the uploaded file object
        """

        uploaded_file_dict = {
            "filename": filename,
            "s3_key": s3_key,
            "short_url": short_url,
        }
        agent_uploaded_file = UploadedFile(**uploaded_file_dict)
        return agent_uploaded_file

    async def _upload_output_text_to_s3_and_create_url(
            self,
            text_to_upload: str,
            output_filename: str,
    ) -> str:
        """
        Upload the output text (e.g. translation, summary) to S3 and create a URL
        :param text_to_upload: the text to upload
        :param output_filename: the name of the output file
        :return: the URL
        """
        text_bytes = BytesIO(text_to_upload.encode("utf-8"))

        return await self._upload_bytes_to_s3_and_create_urls(
            file_bytes=text_bytes.read(),
            output_filename=output_filename
        )

    async def _upload_bytes_to_s3_and_create_urls(self,
                                                  file_bytes: bytes,
                                                  output_filename: str) -> str:
        """
        Upload file bytes to S3 and create a URL
        :param file_bytes: the file bytes to upload
        :param output_filename: the name of the output file
        :param number_of_tokens: the number of tokens in the file
        :return: the URL
        """
        file_bytes = BytesIO(file_bytes)
        output_s3_key = S3_KEY_TEMPLATE.format(
            demo_name=self.agent_session.demo_name,
            session_id=self.agent_session.id,
            filename=output_filename,
        )

        await upload_bytes_to_s3(
            file_data=file_bytes,
            bucket_name=S3_BUCKET_NAME,
            s3_key=output_s3_key,
        )

        # Create a short URL and slack formatted link
        file_presigned_url = create_presigned_url(
            S3_BUCKET_NAME, output_s3_key, expiration=3600
        )
        file_presigned_url = file_presigned_url.replace("/minio:", "/localhost:")

        self.agent_session.user_uploaded_files.append(
            self._create_uploaded_file_object(
                filename=output_filename,
                s3_key=output_s3_key,
                short_url=file_presigned_url,
            )
        )

        return file_presigned_url
