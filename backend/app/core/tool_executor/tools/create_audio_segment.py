import logging
import traceback
import uuid
from typing import Optional, Dict

from pydantic import Field

from app.config import get_settings
from app.core.tool_executor.tools import AgentTool
from app.models.audio_segment_model import AudioSegment
from app.models.character import Character
from app.schemas.tool_model import ToolInput
from app.utils.aws_utils import upload_bytes_to_s3_and_create_urls
from app.utils.audio_generation_utils import TTSGenerator, TTSParams, VoiceSettings, SoundGenerationParams


class CreateAudioSegmentTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.CreateAudioSegment.get_schema(replacements)

    class CreateAudioSegment(ToolInput):
        """Create an engaging and interesting audio segment based on the characters and the audio content is required to be generated (Speech, sounds effects or music)."""
        segment_index: int = Field(...,
                                   description="The index of the segment in the audio content. You must use it to keep track of the order of the segments or for updating a specific segment whether it is speech, music, or sound effects.")
        scene_index: int = Field(...,  # Added scene_index
                                 description="The index of the scene this audio segment belongs to.")
        
        if get_settings().elevenlabs_api_key is None:
            character_id: str = Field(...,
                                    description="The UUID of the character that will be speaking in the segment from one of the created characters.")
            segment_text: str = Field(...,
                                    description="The text that will be spoken in the segment by the character. The text will be converted to speech.")
            
        else:
            music_and_sound_effects: bool = Field(False,
                                    description="If `True`, the text will be used as the script for the music and sound effects but it can't create songs or soundbites. If `False`, the text will be converted to speech.")
        
            music_or_sound_effect_duration: int = Field(5,
                                    description="The duration of the music or sound effect in seconds. This field is only required if `music_and_sound_effects` is set to `True`. The minimum duration is 1 second and maximum duration is 22 seconds.")
            character_id: str = Field(...,
                                    description="The UUID of the character that will be speaking in the segment from one of the created characters. Use `music_and_sound_effects` if the segment is a music or sound effect segment.")
            segment_text: str = Field(...,
                                    description="The text that will be spoken in the segment by the character. The text will be converted to speech if `music_and_sound_effects` is set to `False` otherwise the text will be used as the script for the music and sound effects (e.g. rain, thunder, a hand knocking on the door, classic music, late night show intro with a beat and jazz music) etc.).")
            
        
        speech_style: float = Field(0.0,
                                    description="The style exaggeration of the speech. The value should be between 0.0 and 0.5. A value of 0.0 means no exaggeration, and a value of 0.5 means maximum exaggeration.")

    def get_character_by_id(self, character_id: str) -> Optional[Character]:
        characters = self.agent_session.characters_created

        for character in characters:
            if character.character_id == character_id:
                return character
        return None

    async def create_and_upload_audio_segment(self, character: Character, tool_input: CreateAudioSegment) -> dict:
        generator = TTSGenerator()

        # Prepare the TTSParams
        if tool_input.music_and_sound_effects:
            params = SoundGenerationParams(
                text=tool_input.segment_text,
                duration_seconds=min(tool_input.music_or_sound_effect_duration, 22),
            )
        else:
            params = TTSParams(
                text=tool_input.segment_text,
                voice_id=character.voice_id,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.8,
                    style=tool_input.speech_style,
                    use_speaker_boost=True,
                ),
            )

        try:
            if tool_input.music_and_sound_effects:
                audio_output = await generator.generate_sound_async(params=params)
            else:
                audio_output = await generator.generate_speech_async(params=params)

            audio_bytes = audio_output["audio_bytes"]
            alignment_dict = audio_output["alignment_dict"]

            # Calculate word start and end times
            words = tool_input.segment_text.split(' ')
            word_start_times = []
            word_end_times = []
            char_index = 0

            if 'character_start_times_seconds' in alignment_dict and 'character_end_times_seconds' in alignment_dict:
                for word in words:
                    start_time = alignment_dict['character_start_times_seconds'][char_index]
                    end_time = alignment_dict['character_end_times_seconds'][char_index + len(word) - 1]
                    word_start_times.append(start_time)
                    word_end_times.append(end_time)
                    char_index += len(word) + 1  # +1 for the space character

            if tool_input.music_and_sound_effects:
                duration = params.duration_seconds
            else:
                duration = word_end_times[-1] if word_end_times else 0

            # Upload audio file to S3
            audio_introduction_url = await upload_bytes_to_s3_and_create_urls(
                file_bytes=audio_bytes,
                demo_name=self.agent_session.demo_name,
                session_id=self.agent_session.id,
                output_filename=f"{self.agent_session.id}_segment_{tool_input.segment_index}_{str(uuid.uuid4())}.mp3",
            )

            output = {
                "audio_introduction_url": audio_introduction_url,
                "duration": duration,
                "alignment_dict": {
                    "word_start_times": word_start_times,
                    "word_end_times": word_end_times,
                }
            }

            return output
        except Exception as e:
            logging.error(f"Error generating or uploading audio: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    async def create_audio_segment(self, tool_input: CreateAudioSegment) -> dict:
        logging.info(f"Creating audio segment for scene {tool_input.scene_index}, segment {tool_input.segment_index}")
        logging.info(f"Current audio segments: {[seg.segment_index for seg in self.agent_session.audio_segments]}")

        if not tool_input.music_and_sound_effects:
            character = self.get_character_by_id(tool_input.character_id)
        else:
            character = self.get_character_by_id("music_and_sound_effects")

        if character is None:
            raise Exception(f"Character with ID {tool_input.character_id} not found.")

        audio_segment_output = await self.create_and_upload_audio_segment(character=character, tool_input=tool_input)
        audio_segment_url = audio_segment_output["audio_introduction_url"]
        alignment_dict = audio_segment_output["alignment_dict"]
        duration = audio_segment_output["duration"]

        existing_segment = next(
            (seg for seg in self.agent_session.audio_segments if seg.segment_index == tool_input.segment_index), None)

        if tool_input.music_and_sound_effects:
            tool_input.segment_text = f"🎵🎶 {tool_input.segment_text} 🎶🎵"

        if existing_segment:
            logging.info(f"Updating existing segment {tool_input.segment_index}")
            # Update existing audio segment
            existing_segment.segment_text = tool_input.segment_text
            existing_segment.audio_segment_url = audio_segment_url
            existing_segment.character_name = character.name if character else existing_segment.character_name
            existing_segment.character_photo_url = character.photo_url if character else existing_segment.character_photo_url
            existing_segment.character_colour = character.background_colour if character else existing_segment.character_colour
            existing_segment.alignment_info = alignment_dict
            existing_segment.shared_with_user = True
            existing_segment.duration = duration
            existing_segment.scene_index = tool_input.scene_index
            audio_segment_dict = existing_segment.to_mongo().to_dict()
        else:
            logging.info(f"Creating new segment {tool_input.segment_index}")
            # Create a new audio segment
            audio_segment = AudioSegment(
                segment_text=tool_input.segment_text,
                audio_segment_url=audio_segment_url,
                character_name=character.name if character else None,
                character_photo_url=character.photo_url if character else None,
                character_colour=character.background_colour if character else None,
                alignment_info=alignment_dict,
                shared_with_user=True,
                duration=duration,
                scene_index=tool_input.scene_index
            )

            self.agent_session.add_audio_segment(audio_segment)
            audio_segment_dict = audio_segment.to_mongo().to_dict()

        audio_segment_dict["created_at"] = audio_segment_dict["created_at"].isoformat()

        logging.info(f"Audio segment created/updated: {audio_segment_dict}")
        logging.info(f"Updated audio segments: {[seg.segment_index for seg in self.agent_session.audio_segments]}")

        return audio_segment_dict

    async def execute(self):
        tool_input = self.CreateAudioSegment(**self.tool_args)
        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "fluent:play-circle-hint-20-regular"
        tool_icon_successful = "fluent:play-20-filled"
        tool_icon_error = "fluent:play-20-filled"

        if not hasattr(tool_input, "music_and_sound_effects"):
            tool_input.music_and_sound_effects = False
            tool_input.music_or_sound_effect_duration = 5
            
        try:
            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Creating audio segment #{tool_input.segment_index}",
                                                   tool_icon_waiting):
                yield update

            new_audio_segment = await self.create_audio_segment(tool_input)

            async for update in self.stream_update(tool_call_id, "new_voice_recording", new_audio_segment):
                yield update

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(
                content=f"Audio segment #{tool_input.segment_index} created successfully.")
            self.add_additional_system_message(
                content=
                (
                    "The audio segment has been created successfully. "
                    "Please proceed with the next audio segment or finish the audio content creation if all segments have been created.\n"
                    "After creating each audio segment, it is automatically added to a media player for the user to listen to (on the right side of the screen) so you don't need to summarize the audio segment in the chat."
                )
            )

            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Created audio segment #{tool_input.segment_index} successfully.",
                                                   tool_icon_successful):
                yield update
        except Exception as e:
            logging.error(f"Error creating audio segment: {str(e)}")

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Error creating audio segment: {str(e)}")
            self.add_additional_system_message(
                content="Explain why the audio segment creation failed and provide guidance on how to proceed.")
            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   f"Failed to create audio segment #{tool_input.segment_index} due to an internal error.",
                                                   tool_icon_error):
                yield update