from typing import Optional, List, Dict
from pydantic import Field, BaseModel

from app.core.tool_executor.tools import AgentTool
from app.schemas.tool_model import ToolInput
import uuid
import json
import litellm
import logging
import traceback
class CreateAudioOutlineTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.CreateAudioOutline.get_schema(replacements)

    class CreateAudioOutline(ToolInput):
        """Create an outline for the audio content to ensure coherent scene generation."""
        content_type: str = Field(..., description="The type of content being created (e.g., podcast, story, comedy_sketch, late_night_show).")
        number_of_scenes: Optional[int] = Field(4, description="The total number of scenes to be generated.")
        content_description: str = Field(..., description="A detailed description of the overall content.")
        content_language: Optional[str] = Field("English", description="The language of the content.")
        extracted_knowledge: str = Field(..., description="All the relevant information extracted from the web, uploaded documents and text files in order to create coherent scenes. Leave empty if no information was extracted.")

    async def _create_audio_outline(self, tool_input: CreateAudioOutline) -> Dict[str, any]:
        content_title = self.agent_session.content_title
        content_subtitle = self.agent_session.content_subtitle
        characters = self.agent_session.characters_created

        # Check if title, subtitle, and characters are present
        if not content_title or not content_subtitle:
            error_message = "Title and subtitle are required. Please proceed by creating a title and subtitle afterwards create the characters (if not created) before generating the audio outline."
            self.add_additional_system_message(content=error_message)
            raise Exception(error_message)

        if not characters or (len(characters) == 1 and characters[0].character_id == "music_and_sound_effects"):
            error_message = "At least one non-music character is required (`music_and_sound_effects` doesn't count as it generates music and sound effects). Please proceed by creating the characters before generating the audio outline."
            self.add_additional_system_message(content=error_message)
            raise Exception(error_message)

        # Create a detailed description of each character
        character_descriptions = []
        for character in characters:
            char_desc = (
                f"Character ID: {character.character_id}\n"
                f"Name: {character.name}\n"
                f"Role: {character.role}\n"
                f"Description: {character.description}\n"
                f"Personality: {character.personality}\n"
                f"Is Fictional: {character.is_fictional}\n"
            )
            character_descriptions.append(char_desc)

        system_message = {
            "role": "system",
            "content": (
                "You are an assistant tasked with creating a detailed audio content outline using the content details provided. "
                "Ensure the outline is structured, coherent, and tailored to the specified content type and language. "
                "Write scene descriptions that are detailed, connect to other scenes, and produce high-quality, human-like audio content. "
                "Add the `Melody` character to every scene that requires music or sound effects. "
                "The output should be a JSON object with all necessary details for each scene."
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Create an outline for an audio content with the following details:\n"
                f"Title: {content_title}\n"
                f"Subtitle: {content_subtitle}\n"
                f"Content Type: {tool_input.content_type}\n"
                f"Content Description: {tool_input.content_description}\n"
                f"Content Language: {tool_input.content_language}\n"
                f"Number of Scenes: {tool_input.number_of_scenes}\n"
                f"Available Characters:\n{'-' * 20}\n" + "\n".join(character_descriptions) + f"\n{'-' * 20}\n"
                f"Extracted Knowledge from uploaded documents and text files (core to the audio content to be generated): {tool_input.extracted_knowledge}\n\n"
                f"Ensure each scene description includes the language specification and follows high-quality, human-like audio content guidelines. "
                f"Use the character details provided to create appropriate dialogues in each scene. "
                f"Decide the characters that will be present in each scene and the duration of each scene. You must refer to the characters using their character_id in the characters array in order to be able to retrieve them later to generate the audio segments."                                                                             
                f"Provide the output in the following JSON format:\n"
                f'{{\n  "scenes": [\n      {{\n        "scene_index": 1,\n        "scene_description": "Scene description with language(s) specification",\n        "duration_minutes": 5,\n        "characters": ["Character_id_1", "Character_id_2"]\n      }},\n      ...\n    ]\n  }}\n}}'
            )
        }

        logging.info("Sending prompt to GPT-4O to generate audio content outline.")

        class Scene(BaseModel):
            scene_index: int
            scene_description: str
            duration_minutes: int
            characters: List[str]
        
        class AudioOutline(BaseModel):
            scenes: List[Scene]

        response = await litellm.acompletion(
            model='gpt-4o-2024-11-20',
            messages=[system_message, user_message],
            max_tokens=4096,
            temperature=0.7,
            fallbacks=['gpt-4o', 'gpt-4o-mini'],
            response_format=AudioOutline
        )

        json_response = json.loads(response.choices[0].message.content)

        if "scenes" in json_response and isinstance(json_response["scenes"], list):
            outline = {}
            outline["content_type"] = tool_input.content_type
            outline["number_of_scenes"] = tool_input.number_of_scenes
            outline["extracted_knowledge"] = tool_input.extracted_knowledge
            outline["content_description"] = tool_input.content_description
            outline["content_language"] = tool_input.content_language
            outline["scenes"] = json_response["scenes"]

            for scene in outline["scenes"]:
                scene["status"] = "pending"

            # Store the outline in the session
            self.agent_session.content_outline = outline
            self.agent_session.save()
            return {"outline": outline}
        else:
            logging.error(f"Failed to generate audio outline: {json_response}")
            raise Exception("Failed to generate audio outline")

    async def execute(self):
        tool_input = self.CreateAudioOutline(**self.tool_args)
        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "mdi:playlist-edit"
        tool_icon_successful = "mdi:playlist-check"
        tool_icon_error = "mdi:playlist-remove"

        try:
            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Generating audio content outline...",
                                                   tool_icon_waiting):
                yield update

            outline_job = await self._create_audio_outline(tool_input)
            self.add_openai_function_response(
                content=f"Audio content outline created successfully: {outline_job}"
            )
            self.add_additional_system_message(
                content=f"Share the audio content outline with the user in a brief and concise manner."
            )
            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Generated audio content outline successfully.",
                                                   tool_icon_successful):
                yield update
        except Exception as e:
            self.add_openai_function_response(
                content=f"Error creating audio content outline: {str(e)}"
            )
            self.add_additional_system_message(
                content=f"Explain why the audio content outline creation failed and provide guidance on how to proceed."
            )
            logging.error(f"Failed to create audio content outline due to an internal error: {str(e)}")
            logging.error(traceback.format_exc())
            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   f"Failed to create audio content outline due to an internal error.",
                                                   tool_icon_error):
                yield update

            # Yield the error as the final update
            yield {"type": "tool_error", "content": str(e)}