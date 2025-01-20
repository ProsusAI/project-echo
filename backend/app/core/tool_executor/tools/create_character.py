import asyncio
import base64
import json
import logging
import uuid
from typing import Optional, Dict

import litellm
import tenacity
from pydantic import Field

from app.config import ValidCharacterColour
from app.core.tool_executor.tools import AgentTool
from app.models.character import Character
from app.schemas.tool_model import ToolInput
from app.utils.aws_utils import upload_bytes_to_s3_and_create_urls
from app.utils.audio_generation_utils import TTSGenerator, TTSParams
from app.utils.image_generation_utils import (
    ImageGeneration,
    ImageGenerationParams,
    StableDiffusionModel,
    OutputFormat,
    AspectRatio
)



class CreateCharacterTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.CreateCharacter.get_schema(replacements)

    class CreateCharacter(ToolInput):
        """Create a character based on the user's requirements."""

        name: str = Field(...,
                          description="The name of the character.")
        gender: str = Field(...,
                            description="The gender of the character if applicable.")
        role: str = Field(...,
                          description="The role of the character (e.g. protagonist, antagonist, sidekick, etc.).")
        description: str = Field(...,
                                 description="A description of the character which includes a brief biography, list of facts about the character, and any other relevant information.")
        personality: str = Field(...,
                                 description="The personality traits of the character (e.g. kind, intelligent, silly, short-tempered, etc.).")
        voice_id: str = Field(...,
                              description="The voice ID of the character based on the list of available voice IDs.")
        is_fictional: bool = Field(...,
                                   description="Whether the character is fictional or non-fictional.")
        colour: ValidCharacterColour = Field(...,
                                             description=f"A light hex background colour for the character's card that is unique to the character and works well with black text. Choose from: {', '.join([colour.value for colour in ValidCharacterColour])}")

    @tenacity.retry(
        wait=tenacity.wait_fixed(5),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(Exception),
    )
    async def _generate_photo_prompt(self, tool_input: CreateCharacter) -> str:
        system_message = {
            "role": "system",
            "content": (
                "You are tasked with writing a detailed image generation prompt in JSON for dall-e-3 to create a close-up image of a character. "
                "Determine the prompt details based on the character's name, role, description, personality, and whether the character is fictional or non-fictional.\n"
                "For example, if the character's name is 'Alice', role is 'protagonist', description is 'a young girl who loves to explore the world', personality is 'curious and adventurous', and the character is fictional, "
                'the prompt could be: {"prompt": "a close-up portrait of a girl with blonde hair and blue eyes with a curious and adventurous expression, and background of the world map."}'
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Create a close-up image of a character named {tool_input.name} who is a {tool_input.role}. "
                f"The character is {tool_input.description} and has a {tool_input.personality} personality. "
                f"The character is {'' if tool_input.is_fictional else 'non-'}fictional. "
                f"Gender (if Applicable): {tool_input.gender}"
            )
        }

        response = await litellm.acompletion(
            model='gpt-4o-mini',
            messages=[system_message, user_message],
            max_tokens=256,
            max_retries=2,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        json_response = json.loads(response.choices[0].message.content)

        if "prompt" in json_response:
            return json_response["prompt"]
        else:
            logging.error(f"Failed to generate photo prompt: {json_response}")
            raise

    async def _generate_character_image(self, tool_input: CreateCharacter) -> str:
        photo_prompt = await self._generate_photo_prompt(tool_input=tool_input)
        response = await litellm.aimage_generation(prompt=photo_prompt,
                                                   model="dall-e-3",
                                                   size="1024x1024",
                                                   quality="standard",
                                                   n=1,
                                                   max_retries=2,
                                                   response_format="b64_json")
        image_as_bytes = base64.b64decode(response.data[0]['b64_json'])
        random_id = str(uuid.uuid4())
        return await upload_bytes_to_s3_and_create_urls(
            file_bytes=image_as_bytes,
            demo_name=self.agent_session.demo_name,
            session_id=self.agent_session.id,
            output_filename=f"{tool_input.name}_{random_id}.webp",
        )

    async def _generate_character_image_using_sd(self, tool_input: CreateCharacter) -> str:
        photo_prompt = await self._generate_photo_prompt(tool_input=tool_input)
        params = ImageGenerationParams(
            model=StableDiffusionModel.SD3,
            prompt=photo_prompt,
            output_format=OutputFormat.JPEG,
            aspect_ratio=AspectRatio.SQUARE,
        )

        generator = ImageGeneration()
        image_bytes = await generator.generate_image_async(params)

        random_id = str(uuid.uuid4())
        short_url = await upload_bytes_to_s3_and_create_urls(
            file_bytes=image_bytes,
            demo_name=self.agent_session.demo_name,
            session_id=self.agent_session.id,
            output_filename=f"{tool_input.name}_{random_id}.webp",
        )
        return short_url

    @tenacity.retry(
        wait=tenacity.wait_fixed(5),
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(Exception),
    )
    async def _generate_character_audio_introduction_transcript(self, tool_input: CreateCharacter) -> str:
        system_message = {
            "role": "system",
            "content": (
                "You are tasked with writing a detailed transcript in JSON to create an audio introduction for a character. "
                "Determine the transcript details based on the character's name, role, description, personality, and whether the character is fictional or non-fictional.\n"
                "For example, if the character's name is 'Alice', role is 'protagonist', description is 'a young girl who loves to explore the world', personality is 'curious and adventurous', and the character is fictional, "
                'the transcript could be: {"transcript": "Hello, my name is Alice. I play a key role in the story, I am a young, curious and adventurous girl who loves to explore the world."}'
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Create an audio introduction for a character named {tool_input.name} who is a {tool_input.role}. "
                f"The character is {tool_input.description} and has a {tool_input.personality} personality. "
                f"The character is {'' if tool_input.is_fictional else 'non-'}fictional."
            )
        }

        response = await litellm.acompletion(
            model='gpt-4o-mini',
            messages=[system_message, user_message],
            max_tokens=4096,
            max_retries=2,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        json_response = json.loads(response.choices[0].message.content)

        if "transcript" in json_response:
            return json_response["transcript"]
        else:
            logging.error(f"Failed to generate audio introduction: {json_response}")
            raise

    async def _generate_character_audio_introduction(self, tool_input: CreateCharacter) -> str:
        character_introduction_transcript = await self._generate_character_audio_introduction_transcript(
            tool_input=tool_input
        )

        generator = TTSGenerator()
        params = TTSParams(
            text=character_introduction_transcript,
            voice_id=tool_input.voice_id,
            model_id="eleven_turbo_v2_5"
        )

        try:
            audio_output = await generator.generate_speech_async(params=params)
            random_id = str(uuid.uuid4())
            audio_bytes = audio_output["audio_bytes"]
            audio_introduction_url = await upload_bytes_to_s3_and_create_urls(
                file_bytes=audio_bytes,
                demo_name=self.agent_session.demo_name,
                session_id=self.agent_session.id,
                output_filename=f"{tool_input.name}_introduction_{random_id}.mp3",
            )

            return audio_introduction_url
        except Exception as e:
            # Handle any exceptions that might occur during audio generation or upload
            print(f"Error generating or uploading audio: {str(e)}")
            raise

    async def _create_new_character(self, tool_input: CreateCharacter) -> dict:
        photo_url_task = self._generate_character_image_using_sd(tool_input)
        audio_introduction_url_task = self._generate_character_audio_introduction(tool_input)

        # Run both tasks concurrently
        photo_url, character_audio_introduction_url = await asyncio.gather(
            photo_url_task, audio_introduction_url_task
        )

        new_character = Character(
            character_id=str(uuid.uuid4()),
            name=tool_input.name,
            role=tool_input.role,
            description=tool_input.description,
            personality=tool_input.personality,
            voice_id=tool_input.voice_id,
            is_fictional=tool_input.is_fictional,
            photo_url=photo_url,
            introduction_audio_url=character_audio_introduction_url,
            background_colour=tool_input.colour,
            shared_with_user=True,
        )
        self.agent_session.characters_created.append(new_character)
        new_character_w_key_data = new_character.to_mongo().to_dict()
        new_character_w_key_data["created_at"] = new_character_w_key_data["created_at"].isoformat()

        return new_character_w_key_data


    def _check_if_character_exists(self, tool_input: CreateCharacter) -> bool:
        for character in self.agent_session.characters_created:
            if character.name == tool_input.name:
                return True
        return False

    async def execute(self):
        tool_input = self.CreateCharacter(**self.tool_args)
        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "mdi:user-clock-outline"
        tool_icon_successful = "mdi:user-check-outline"
        tool_icon_error = "mdi:user-block-outline"
        try:
            if self._check_if_character_exists(tool_input):
                self.add_additional_system_message(content=f"Character with the name `{tool_input.name}` already exists. Please continue with the rest of the characters creation if any are left.")
            else:
                async for update in self.stream_update(tool_call_id, "tool_progress", f"Creating a character for `{tool_input.name}`.", tool_icon_waiting):
                    yield update

                new_character = await self._create_new_character(
                    tool_input=tool_input,
                )

                new_character_llm_copy = new_character.copy()

                # Stream the new character to the user
                async for update in self.stream_update(tool_call_id, "new_character", content=new_character):
                    yield update

                del new_character_llm_copy["photo_url"]
                del new_character_llm_copy["introduction_audio_url"]
                function_response = f"Character created successfully: {new_character_llm_copy}"
                self.add_openai_function_call(arguments=self.tool_args)
                self.add_openai_function_response(content=function_response)
                self.add_additional_system_message(
                    content=(
                        "Character creation successful. Don't provide the user with the character details. "
                        "The new character has been added to the user's roster. "
                        "The user can view and manage all characters in the character drawer "
                        "located on the left side of the screen. "
                        "Ask if the user would like to create another character or proceed with your current roster to create the content outline?"
                    )
                )

                async for update in self.stream_update(tool_call_id, "tool_progress", f"Created a character for `{tool_input.name}` successfully.", tool_icon_successful):
                    yield update
        except Exception as e:
            logging.error(f"Failed to create character: {e}")

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Failed to create character: {e}")
            self.add_additional_system_message(
                content="Explain why the tool failed and how the user can fix it.")
            async for update in self.stream_update(tool_call_id, "tool_error", f"Failed to create character: `{tool_input.name}`", tool_icon_error):
                yield update
