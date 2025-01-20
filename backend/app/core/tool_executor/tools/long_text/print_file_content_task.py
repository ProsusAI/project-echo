import uuid

from litellm import token_counter
from app.core.tool_executor.tools.long_text.long_text_handling_task import LongTextHandlingTask


class PrintFileContentTask(LongTextHandlingTask):
    async def execute(self):
        try:
            if self.user_uploaded_file is None:
                async for update in self.handle_file_not_found():
                    yield update
                return

            tool_call_id = str(uuid.uuid4())

            yield {
                "tool_call_id": tool_call_id,
                "message_type": "tool_progress",
                "content": f"Reading the content of {self.input_filename}...",
                "icon": "mdi:file-eye"
            }

            file_content = self._read_file_content_from_s3()
            file_num_tokens = token_counter(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": file_content
                }]
            )
            max_number_of_tokens = 32000
            if file_num_tokens and file_num_tokens > max_number_of_tokens:
                message = f"Text extraction failed for `{self.input_filename}` because it contains more than `{max_number_of_tokens}` tokens."
                self.add_openai_function_call(arguments=self.tool_args)
                self.add_openai_function_response(content=message)
                self.add_additional_system_message(content=" Create a detailed summary of text file and ask 5-20 relevant questions based on the summary and the user's request to extract the relevant information.")
                yield {
                    "tool_call_id": self.tool_call_id,
                    "message_type": "tool_error",
                    "content": message,
                    "icon": "mdi:file-alert"
                }
            else:
                self.add_openai_function_call(arguments=self.tool_args)
                self.add_openai_function_response(content=file_content)
                yield {
                    "tool_call_id": tool_call_id,
                    "message_type": "tool_progress",
                    "content": f"Content of {self.input_filename} has been read successfully",
                    "icon": "mdi:file-check"
                }
        except Exception as e:
            async for update in self.handle_exception(e, "print file content"):
                yield update
