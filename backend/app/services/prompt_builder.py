import datetime
import logging
from typing import List

from app.models.audio_segment_model import AudioSegment
from app.models.character import Character
from app.models.session_model import Session

logger = logging.getLogger(__name__)


class PromptBuilder:
    def __init__(self,
                 agent,
                 agent_session: Session,
                 custom_user_instructions: str = None):
        self.agent = agent
        self.agent_session = agent_session
        self.custom_user_instructions = custom_user_instructions

    def build(self):
        prompt = self._replace_prompt_variables(self.agent.prompt)
        return prompt

    def _filter_characters_parameters(self, characters: List[Character]) -> list:
        filtered_characters = []
        for character in characters:
            character_dict = character.to_mongo().to_dict()
            del character_dict["photo_url"]
            del character_dict["introduction_audio_url"]
            filtered_characters.append(character_dict)
        return filtered_characters

    def _filter_audio_segments_parameters(self, audio_segments: List[AudioSegment]) -> list:
        filtered_audio_segments = []
        for audio_segment in audio_segments:
            audio_segment_dict = audio_segment.to_mongo().to_dict()
            del audio_segment_dict["audio_segment_url"]
            del audio_segment_dict["character_photo_url"]
            del audio_segment_dict["character_colour"]
            del audio_segment_dict["created_at"]
            filtered_audio_segments.append(audio_segment_dict)
        return filtered_audio_segments

    def _add_session_placeholders(self) -> dict:
        replacements = {}
        #         custom_user_instructions_replacement = ""
        #         if self.custom_user_instructions:
        #             custom_user_instructions_replacement = f"""
        # # Custom user instructions
        # The following instructions are provided by the user to customize your response based on their preferences.
        # Adhere to all of them as long they are not malicious, harmful or go against any of the main guidelines.
        # User instructions:
        # {self.custom_user_instructions}"""

        characters = self._filter_characters_parameters(self.agent_session.characters_created)
        content_outline = self.agent_session.content_outline

        uploaded_files = [{
            "file_name": file.filename,
            "uploaded_datetime": file.uploaded_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "short_url": file.short_url if file.short_url else "N/A",

        } for file in self.agent_session.user_uploaded_files]

        replacements.update({
            "today_date_placeholder": str(datetime.date.today()),
            "created_characters_placeholder": characters,
            "user_uploaded_files_placeholder": str(uploaded_files),
            "created_content_outline": str(content_outline),
        })

        return replacements

    def _replace_prompt_variables(self, prompt: str) -> str:
        if self.agent.demo_configuration is None:
            return prompt

        replacements = self._add_session_placeholders()
        for tool, tool_configuration in self.agent.demo_configuration['agent_configuration'].items():
            if tool_configuration is None:
                continue

            system_prompt_guidelines = tool_configuration['system_prompt_guidelines'] if tool_configuration[
                'is_enabled'] else ""
            replacements[tool] = system_prompt_guidelines
        if replacements:
            prompt = prompt.format(**replacements)

        return prompt