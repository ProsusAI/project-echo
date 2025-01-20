import logging
import traceback
import uuid
from typing import Optional, Dict
from datetime import datetime

from pydantic import Field

from app.core.tool_executor.tools import AgentTool
from app.models.audio_segment_model import AudioSegment
from app.schemas.tool_model import ToolInput
from app.utils.aws_utils import upload_bytes_to_s3_and_create_urls
from app.utils.audio_generation_utils import TTSGenerator, SoundGenerationParams

import litellm

class CreateSoundEffectTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.CreateSoundEffect.get_schema(replacements)

    class CreateSoundEffect(ToolInput):
        """Create a sound effect or music segment for the audio content."""
        scene_index: int = Field(..., description="The index of the scene or act in the audio content.")
        effect_description: str = Field(..., description="A detailed description of the desired sound effect or music.")
        duration_seconds: int = Field(..., description="The duration of the sound effect or music in seconds (min 0.5, max 22 seconds).")
        rewrite_segment: Optional[bool] = Field(False, description="Flag to indicate if the sound effect segment should be rewritten.")

    async def _generate_sound_effect_prompt(self, tool_input: CreateSoundEffect) -> str:
        system_message = {
            "role": "system",
            "content": (
                "You are an expert sound designer tasked with creating detailed prompts for generating sound effects or music. "
                "Your goal is to translate the given effect description into a clear, specific prompt that can be used "
                "to generate the desired audio effect. Use the following examples as inspiration:\n\n"
                "- A deep, dramatic braam sound, perfect for creating tension and impact in a trailer\n"
                "- Vintage radio, frequency change, interference, radio static\n"
                "- A scary and weird sound from space, drums are getting louder and louder\n"
                "- Ethereal, shimmering atmosphere for a mysterious scene\n"
                "- Dogs barking\n"
                "- Interface opening with a smooth whoosh\n"
                "- Sound of large fire burning intensely, roaring flames creating a constant crackling and whooshing noise\n"
                "- Sirens in the distance, city sounds\n"
                "- Horses galloping by\n"
                "- Best emotional piano solo\n"
                "- A lion roaring\n"
                "- Footsteps on concrete\n"
                "- Machine Gun\n"
                "- Gunshots in an indoor shooting range with reverberation and echo\n"
                "- Short atmosphere magic start level in casual game\n"
                "- Bubbling and boiling sound from a large cauldron in a medieval dungeon\n"
                "- Choir of angels\n"
                "- Tribal drums starting slow and building to a frenetic climax\n"
                "- The rapid, staccato roll of a snare drum, with a crisp, precise rhythm\n"
                "- A dramatic, dissonant, orchestral riser with swelling strings and brass\n"
                "- Enchanting melody from a magical harp\n"
                "- Pizzicato string quartet for a playful, bouncy effect\n"
                "- Saxophone solo in A minor\n\n"
                "IMPORTANT: Your output should be a single, concise sentence describing the sound effect, "
                "no longer than 450 characters. Do not include any explanations or additional context."
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Create a concise prompt (max 450 characters) for the following sound effect or music:\n"
                f"Description: {tool_input.effect_description}\n"
                f"Duration: {tool_input.duration_seconds} seconds\n\n"
                f"Provide only the sound description, no additional explanations."
            )
        }

        response = await litellm.acompletion(
            model='gpt-4o-2024-11-20',
            messages=[system_message, user_message],
            max_tokens=100,
            temperature=0.7,
            fallbacks=['gpt-4o', 'gpt-4o-mini']
        )

        return response.choices[0].message.content.strip()

    async def create_sound_effect(self, tool_input: CreateSoundEffect) -> dict:
        effect_prompt = await self._generate_sound_effect_prompt(tool_input)
        
        generator = TTSGenerator()

        # Adjust the duration to be within the allowed range (0.5 to 22 seconds)
        adjusted_duration = min(max(tool_input.duration_seconds, 0.5), 22)

        params = SoundGenerationParams(
            text=effect_prompt,
            duration_seconds=adjusted_duration,
        )

        try:
            audio_output = await generator.generate_sound_async(params=params)
            audio_bytes = audio_output["audio_bytes"]

            audio_url = await upload_bytes_to_s3_and_create_urls(
                file_bytes=audio_bytes,
                demo_name=self.agent_session.demo_name,
                session_id=self.agent_session.id,
                output_filename=f"{self.agent_session.id}_scene_{tool_input.scene_index}_sound_{str(uuid.uuid4())}.mp3",
            )

            melody_character = next((c for c in self.agent_session.characters_created if c.name == "Melody"), None)
            if not melody_character:
                raise ValueError("Melody character not found in the session")

            audio_segment = AudioSegment(
                segment_index=0,  # This will be set correctly by add_audio_segment
                segment_text=f"🎵🎶 {tool_input.effect_description} 🎶🎵",
                audio_segment_url=audio_url,
                character_name=melody_character.name,
                character_photo_url=melody_character.photo_url,
                character_colour=melody_character.background_colour,
                shared_with_user=True,
                duration=adjusted_duration,
                scene_index=tool_input.scene_index,
                position_in_scene=0  # This will be updated when added to the session
            )

            self.agent_session.add_audio_segment(audio_segment)
            
            # Convert the audio segment to a dictionary and ensure datetime objects are serialized
            audio_segment_dict = audio_segment.to_mongo().to_dict()
            for key, value in audio_segment_dict.items():
                if isinstance(value, datetime):
                    audio_segment_dict[key] = value.isoformat()
            
            return audio_segment_dict

        except Exception as e:
            logging.error(f"Error generating sound effect: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    async def execute(self):
        tool_input = self.CreateSoundEffect(**self.tool_args)
        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "fluent:music-note-2-20-regular"
        tool_icon_successful = "fluent:music-note-2-20-filled"
        tool_icon_error = "fluent:music-note-2-20-filled"

        try:
            if tool_input.rewrite_segment:
                # Delete existing sound effect segments for the specified scene_index
                self.agent_session.audio_segments = [
                    segment for segment in self.agent_session.audio_segments
                    if not (segment.scene_index == tool_input.scene_index and segment.character_name == "Melody")
                ]
                self.agent_session.save()
                async for update in self.stream_update(
                    tool_call_id,
                    "tool_progress",
                    f"Rewriting sound effect for scene #{tool_input.scene_index}...",
                    tool_icon_waiting
                ):
                    yield update
            else:
                async for update in self.stream_update(
                    tool_call_id,
                    "tool_progress",
                    f"Creating sound effect for scene #{tool_input.scene_index}...",
                    tool_icon_waiting
                ):
                    yield update

            sound_effect = await self.create_sound_effect(tool_input)

            async for update in self.stream_update(tool_call_id, "new_voice_recording", sound_effect):
                yield update

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(
                content=f"Sound effect for scene #{tool_input.scene_index} created successfully."
            )
            self.add_additional_system_message(
                content=(
                    "The sound effect for the scene has been created successfully. "
                    "Audio segment has been automatically added to the media player for the user to listen to. "
                    "Please proceed with the next scene or finish the audio content creation if all scenes have been created."
                )
            )

            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Created sound effect for scene #{tool_input.scene_index} successfully.",
                                                   tool_icon_successful):
                yield update
        except Exception as e:
            logging.error(f"Error creating sound effect: {str(e)}")

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Error creating sound effect: {str(e)}")
            self.add_additional_system_message(
                content="Explain why the sound effect creation failed and provide guidance on how to proceed."
            )
            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   f"Failed to create sound effect for scene #{tool_input.scene_index} due to an internal error.",
                                                   tool_icon_error):
                yield update