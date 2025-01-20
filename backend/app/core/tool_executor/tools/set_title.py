import logging
import uuid
from typing import Optional, Dict

from pydantic import Field

from app.core.tool_executor.tools import AgentTool
from app.schemas.tool_model import ToolInput


class SetTitleTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.SetTitle.get_schema(replacements)

    class SetTitle(ToolInput):
        """Generate an engaging and suitable title for the voice content that the user would like to create."""
        title: str = Field(...,
                           description="The title of the voice content that the user would like to create. The title should be engaging and suitable for the content.")
        subtitle: str = Field(...,
                              description="The subtitle of the voice content that the user would like to create. The subtitle should provide a brief description of the content.")

    async def execute(self):
        tool_input = self.SetTitle(**self.tool_args)
        tool_call_id = str(uuid.uuid4())
        tool_icon = "fluent:draw-text-20-filled"
        try:
            self.agent_session.content_title = tool_input.title
            self.agent_session.content_subtitle = tool_input.subtitle

            content = {
                "title": tool_input.title,
                "subtitle": tool_input.subtitle
            }
            async for update in self.stream_update(tool_call_id, "new_title", content):
                yield update

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content="Title and subtitle have been set successfully.")
            self.add_additional_system_message(
                content="The title and subtitle have been set successfully. Don't update the user about this.")
            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   "Title and subtitle have been set successfully.", tool_icon):
                yield update
        except Exception as e:
            logging.error(f"Error setting title and subtitle: {str(e)}")

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Error setting title and subtitle: {str(e)}")
            self.add_additional_system_message(
                content="Explain why the title and subtitle could not be set and provide guidance to the user.")
            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   "Something went wrong while setting the title and subtitle.",
                                                   tool_icon):
                yield update
