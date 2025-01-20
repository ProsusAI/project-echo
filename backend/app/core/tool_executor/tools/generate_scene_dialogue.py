import logging
import traceback
import uuid
import asyncio
from typing import Optional, Dict, List

from pydantic import Field, BaseModel

from app.core.tool_executor.tools import AgentTool
from app.models.audio_segment_model import AudioSegment
from app.schemas.tool_model import ToolInput
from app.utils.aws_utils import upload_bytes_to_s3_and_create_urls
from app.utils.audio_generation_utils import TTSGenerator, TTSParams, VoiceSettings, SoundGenerationParams

import litellm
import json
from bson import json_util

class GenerateSceneDialogueTool(AgentTool):

    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.GenerateSceneDialogue.get_schema(replacements)

    class GenerateSceneDialogue(ToolInput):
        """Generate engaging and interesting dialogue for an entire scene or act"""
        scene_index: int = Field(..., description="The index of the scene or act in the audio content.")
        extracted_knowledge: str = Field(None, description="All relevant knowledge extracted from web, documents and conversation history. If no knowledge was extracted, leave this field empty.")
        rewrite_scene: Optional[bool] = Field(False, description="Flag to indicate if the scene should be rewritten.")

    async def _generate_scene_dialogue(self, tool_input: GenerateSceneDialogue) -> Dict[str, List[Dict[str, str]]]:
        # Retrieve the outline from the session
        outline = self.agent_session.content_outline
        if not outline:
            error_message = "Content outline not found. Please create an outline before generating scene dialogues."
            self.add_additional_system_message(content=error_message)
            raise Exception(error_message)
        
        # Get the specific scene details based on scene_index
        scene = next((s for s in outline["scenes"] if s["scene_index"] == tool_input.scene_index), None)
        if not scene:
            raise Exception(f"Scene {tool_input.scene_index} not found in the outline.")

        characters = scene["characters"]
        content_description = outline["content_description"]
        content_language = outline["content_language"]
        scene_description = scene["scene_description"]
        duration_minutes = scene["duration_minutes"]
        content_type = outline["content_type"]

        # Retrieve existing dialogue from the session
        existing_dialogue = ""
        for segment in self.agent_session.audio_segments:
            existing_dialogue += f"{segment.character_id}: {segment.segment_text}\n"

        guidelines = self._get_content_guidelines(content_type)

        # Get detailed character information
        character_details = self._get_character_details(characters)
        
        # Check if Melody is one of the characters
        include_melody_guidelines = "music_and_sound_effects" in characters
        
        melody_guidelines = """
        When including Melody (sound effects and music):
        - Describe sound effects or music cues in brackets, e.g., [Melody: description]
        - Be specific and detailed in your sound effect descriptions
        - Consider the mood, atmosphere, and context of the scene when describing sound effects or music
        - Use sound effects to enhance the storytelling, not just as background noise
        - Examples of good sound effect descriptions:
          - A deep, dramatic braam sound, perfect for creating tension and impact
          - Vintage radio, frequency change, interference, radio static
          - A scary and weird sound from space, drums are getting louder and louder
          - Ethereal, shimmering atmosphere for a mysterious scene
          - Best emotional piano solo
          - Tribal drums starting slow and building to a frenetic climax
          - Enchanting melody from a magical harp
        """ if include_melody_guidelines else ""
        
        system_message = {
            "role": "system",
            "content": (
                "You are a skilled screenwriter tasked with creating engaging and natural dialogue for an audio scene. The dialogue gets converted to audio using a Text to Speech model which may sound out of place if actions (e.g. laughter, etc.) between [] or () are used in the dialouge."
                "Your goal is to write dialogue that sounds human, avoiding any AI-like patterns or responses. "
                "Use natural language, include pauses, interruptions, and realistic conversation flow. "
                "Incorporate character personalities and the scene context into the dialogue. "
                "Ensure consistency with previously generated dialogue and maintain accuracy of facts throughout the content. "
                "Generate the dialogue in the language(s) specified in the content outline. "
                f"The content type for this scene is: {content_type}. "
                f"The content title is: {self.agent_session.content_title}. "
                f"The content subtitle is: {self.agent_session.content_subtitle}. "
                f"Overall audio content description: {content_description}. "
                f"Follow these guidelines for the content:\n\n{guidelines}\n\n"
                f"{melody_guidelines}"
                "Provide the dialogue in a JSON format where each element is an object with 'character' and 'dialogue' keys. "
                "Use the full character ID as provided in the character details. "
                "Maintain the order of the dialogue by using an array of these objects.\n"
                "If the character 'Melody' is included, incorporate appropriate sound effect or music descriptions where she should contribute."
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Create a dialogue for a scene with the following details:\n"
                f"Content title: {self.agent_session.content_title or 'Not specified'}\n"
                f"Content subtitle: {self.agent_session.content_subtitle or 'Not specified'}\n"
                f"Scene description: {scene_description}\n"
                f"Characters:\n{character_details}\n"
                f"Approximate duration: {duration_minutes} minutes\n"
                f"Extracted knowledge: {tool_input.extracted_knowledge or 'None provided'}\n"
                f"Content type: {content_type}\n"
                f"Content language(s): {content_language}\n"
                f"Previous dialogue:\n{existing_dialogue}\n\n"
                f"Don't add actions between [] or () because the dialogue gets converted to audio using a Text to Speech model which make these actions sound out of place."
                f"Include natural pauses, interruptions, and realistic conversation flow. "
                f"Ensure consistency with previous dialogue and maintain accuracy of facts.\n"
                f"Avoid creating sound effects if the content type isn't suitable for them. Only consider intro, outro and transition music in this case. "
                f"Note: If 'Melody' is included among the characters, include entries like {{'character': 'music_and_sound_effects', 'dialogue': '[Sound effect description]'}} where appropriate. "
                f"Ensure that the dialogue is written in the specified language(s) and that the dialogue is consistent with the scene description and the characters' personalities. "
                f"If only one character (Melody doesn't count as it generate sound effects and music) is speaking, the dialogue should be a monologue that fits the character's personality, the scene description and overall content description. "
                f"Characters must not refer to `Melody` in the script as it is only used to generate sound effects and music intro/outro and transitions."
                f"Please provide the dialogue in the following JSON format:\n"
                f'{{"dialogue": [\n'
                f'  {{"character_id": "Character ID", "dialogue": "Their dialogue text"}},\n'
                f'  {{"character_id": "Another Character ID", "dialogue": "Their dialogue"}},\n'
                f'  ...\n'
                f']}}\n'
            )
        }

        class CharacterDialogue(BaseModel):
            character_id: str
            dialogue: str

        class SceneDialogue(BaseModel):
            dialogue: List[CharacterDialogue]

        response = await litellm.acompletion(
            model='gpt-4o-2024-11-20',
            messages=[system_message, user_message],
            max_tokens=4096,
            temperature=0.7,
            fallbacks=['gpt-4o', 'gpt-4o-mini'],
            response_format=SceneDialogue
        )

        logging.info(f"LLM response for scene {tool_input.scene_index}:\n{response.choices[0].message.content}")

        json_response = json.loads(response.choices[0].message.content)

        if "dialogue" in json_response and isinstance(json_response["dialogue"], list):
            dialogue_list = json_response["dialogue"]
            return {"dialogue": dialogue_list}
        else:
            logging.error(f"Failed to generate scene dialogue: {json_response}")
            raise Exception("Failed to generate scene dialogue")

    def _get_content_guidelines(self, content_type: str) -> str:
        generic_guidelines = """
        Generic Guidelines:
         1. Compelling Opening: Start with a strong hook to grab the listener's attention.
         2. Relatable Content: Create content that resonates with your audience's interests and emotions.
         3. Clear and Concise Delivery: Maintain engagement with clear and concise delivery.
         4. Incorporate natural speech patterns into the dialogue, such as pauses, interruptions, fillers like "um" and "uh," laughter ("ha ha ha"), sighs ("aaaahh"), and varied intonations to make the script sound more human and less AI-generated.
         5. Occasionally let characters repeat back dialogue to each other to make the dialogue more natural and less scripted.
         6. Occasionally let characters use interjections like "ha ha ha" or "aaaahh" to express emotions or reactions.
         7. Let characters often cut or interrupt each other to make the dialogue more natural and less scripted.
         8. Occasionally let characters use interjections like "ha ha ha" or "aaaahh" to express emotions or reactions.
        """

        content_specific_guidelines = {
            "podcast": """
        Content-Specific Guidelines for Podcasts:
         1. Consistent Theme and Format: Maintain a consistent theme and format throughout your podcast.
         2. Expert Guests and Interviews: Feature expert guests and conduct insightful interviews.
         3. Engaging Storytelling Techniques: Utilize anecdotes, case studies, and real-life examples.
         4. Structured Episode Planning: Plan each episode with a clear outline.
         5. Audience Interaction and Engagement: Incorporate listener feedback and questions.
         6. Conversational Tone: Encourage a natural and conversational tone.
         7. Use of Everyday Language: Incorporate everyday language, including slang and idioms where appropriate.
        """,
            "story": """
        Content-Specific Guidelines for Stories:
         1. Strong Characters and Plot: Develop strong, relatable characters and a compelling plot.
         2. Descriptive Language: Use vivid and descriptive language to create mental imagery.
         3. Emotional Connection: Evoke emotions through your storytelling.
         4. Varied Pacing and Tone: Match the story's mood with varied pacing and tone.
         5. Natural Dialogue: Write dialogue that reflects natural human speech.
        """,
            "comedy_sketch": """
        Content-Specific Guidelines for Comedy Sketches:
         1. Relatable Humor: Focus on humor that your target audience can relate to.
         2. Tight Script and Timing: Ensure the script is well-timed.
         3. Character Dynamics: Develop interesting and funny character dynamics.
         4. Surprise and Subversion: Use surprise elements and subvert expectations.
         5. Energetic Performance: Deliver with energy and enthusiasm.
         6. Authentic Reactions: Include genuine reactions and spontaneous moments.
        """
        }

        combined_guidelines = generic_guidelines + "\n"
        if content_type in content_specific_guidelines:
            combined_guidelines += content_specific_guidelines[content_type]
        else:
            combined_guidelines += "No specific guidelines available for this content type. Please follow the generic guidelines."

        return combined_guidelines

    def _get_character_details(self, character_ids: List[str]) -> str:
        character_details = ""
        for char_id in character_ids:
            character = next((c for c in self.agent_session.characters_created if c.character_id == char_id), None)
            if character:
                character_details += (
                    f"- ID: {character.character_id}\n"
                    f"  Name: {character.name}\n"
                    f"  Role: {character.role}\n"
                    f"  Description: {character.description}\n"
                    f"  Personality: {character.personality}\n"
                    f"  Is Fictional: {character.is_fictional}\n\n"
                )
        return character_details

    async def generate_audio_segments(self, tool_input: GenerateSceneDialogue, dialogue: List[Dict[str, str]]) -> List[dict]:
        generator = TTSGenerator()

        logging.info(f"Starting to generate audio segments for scene {tool_input.scene_index}")
        logging.info(f"Current audio segments: {[seg.segment_index for seg in self.agent_session.audio_segments]}")

        async def generate_segment(index: int, dialogue_entry: Dict[str, str]):
            character_id = dialogue_entry['character_id']
            text = dialogue_entry['dialogue']

            logging.info(f"Generating segment for character {character_id}")
            character = next((c for c in self.agent_session.characters_created if c.character_id == character_id), None)
            if not character:
                logging.error(f"Character {character_id} not found.")
                return None

            # `Melody` is used to generate sound effects and music
            if character_id == 'music_and_sound_effects':
                # Generate sound effect
                effect_description = text.strip('[]')
                # Define duration or extract from text if possible
                duration_seconds = 3

                params = SoundGenerationParams(
                    text=effect_description,
                    duration_seconds=duration_seconds,
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

                    audio_segment = AudioSegment(
                        segment_index=len(self.agent_session.audio_segments) + index,
                        segment_text=f"🎵🎶 {effect_description} 🎶🎵",
                        audio_segment_url=audio_url,
                        character_id=character.character_id,
                        character_name=character.name,
                        character_photo_url=character.photo_url,
                        character_colour=character.background_colour,
                        shared_with_user=True,
                        duration=duration_seconds,
                        scene_index=tool_input.scene_index,
                        position_in_scene=index
                    )

                except Exception as e:
                    logging.error(f"Error generating sound effect: {str(e)}")
                    logging.error(traceback.format_exc())
                    return None
            else:
                # Generate speech for other characters
                content_language = self.agent_session.content_outline.get("content_language", "English").lower()
                model_id = "eleven_multilingual_v2" if content_language not in ["english", "en"] else "eleven_turbo_v2_5"
                params = TTSParams(
                    text=text,
                    voice_id=character.voice_id,
                    model_id=model_id,
                    voice_settings=VoiceSettings(
                        use_speaker_boost=True,
                    ),
                )
                try:
                    audio_output = await generator.generate_speech_async(params=params)
                    audio_bytes = audio_output["audio_bytes"]
                    alignment_dict = audio_output["alignment_dict"]

                    audio_url = await upload_bytes_to_s3_and_create_urls(
                        file_bytes=audio_bytes,
                        demo_name=self.agent_session.demo_name,
                        session_id=self.agent_session.id,
                        output_filename=f"{self.agent_session.id}_scene_{tool_input.scene_index}_segment_{str(uuid.uuid4())}.mp3",
                    )

                    # Calculate word start and end times
                    words = text.split(' ')
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

                    # Calculate the duration
                    duration = word_end_times[-1] if word_end_times else 0

                    audio_segment = AudioSegment(
                        segment_index=len(self.agent_session.audio_segments) + index,
                        segment_text=text,
                        audio_segment_url=audio_url,
                        character_id=character.character_id,
                        character_name=character.name,
                        character_photo_url=character.photo_url,
                        character_colour=character.background_colour,
                        alignment_info={
                            "word_start_times": word_start_times,
                            "word_end_times": word_end_times,
                        },
                        shared_with_user=True,
                        duration=duration,
                        scene_index=tool_input.scene_index,
                        position_in_scene=index
                    )

                except Exception as e:
                    logging.error(f"Error generating audio for segment: {str(e)}")
                    logging.error(traceback.format_exc())
                    return None

            # Convert the audio_segment to a JSON-serializable dictionary
            segment_dict = json.loads(json_util.dumps(audio_segment.to_mongo().to_dict()))
            
            # Ensure created_at is properly formatted
            if 'created_at' in segment_dict:
                segment_dict['created_at'] = segment_dict['created_at']['$date']

            return index, segment_dict

        # Create tasks with indices
        tasks = [generate_segment(idx, entry) for idx, entry in enumerate(dialogue)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results while preserving order
        segments = []
        for result in results:
            if isinstance(result, Exception) or result is None:
                # Handle exceptions if necessary
                continue
            index, segment_data = result
            segments.append((index, segment_data))

        # Sort segments based on the original index
        segments.sort(key=lambda x: x[0])

        # Extract the segment data
        audio_segments = [segment_data for _, segment_data in segments]

        logging.info(f"Generated {len(audio_segments)} new audio segments")
        logging.info(f"New segment indices: {[seg['segment_index'] for seg in audio_segments]}")

        return audio_segments

    async def execute(self):
        tool_input = self.GenerateSceneDialogue(**self.tool_args)

        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "fluent:play-circle-hint-20-regular"
        tool_icon_successful = "fluent:play-20-filled"
        tool_icon_error = "fluent:error-circle-20-filled"

        # Validate if scenes before the current one have been generated
        if tool_input.scene_index > 1:
            existing_scenes = set(segment.scene_index for segment in self.agent_session.audio_segments)
            missing_scenes = set(range(1, tool_input.scene_index)) - existing_scenes
            if missing_scenes:
                error_message = f"Cannot generate scene {tool_input.scene_index} because the following scenes have not been generated yet: {', '.join(map(str, sorted(missing_scenes)))}. Please generate these scenes first."
                self.add_additional_system_message(content=error_message)
                return

        try:
            if tool_input.rewrite_scene:
                # Delete existing audio segments for the specified scene_index
                deleted_segment_indices = [
                    segment.segment_index for segment in self.agent_session.audio_segments
                    if segment.scene_index == tool_input.scene_index
                ]
                self.agent_session.audio_segments = [
                    segment for segment in self.agent_session.audio_segments
                    if segment.scene_index != tool_input.scene_index
                ]
                
                # Send websocket event for deleted segments
                for index in deleted_segment_indices:
                    async for update in self.stream_update(
                        tool_call_id,
                        "delete_voice_recording",
                        {"segment_index": index}
                    ):
                        yield update

                async for update in self.stream_update(
                    tool_call_id,
                    "tool_progress",
                    f"Rewriting dialogue for scene #{tool_input.scene_index}...",
                    tool_icon_waiting
                ):
                    yield update
            else:
                async for update in self.stream_update(
                    tool_call_id,
                    "tool_progress",
                    f"Generating dialogue for scene #{tool_input.scene_index}...",
                    tool_icon_waiting
                ):
                    yield update

            # Validate characters
            characters_ids = self.agent_session.content_outline.get("characters", [])
            invalid_characters = self._validate_characters(characters_ids)
            if invalid_characters:
                error_message = f"Invalid character IDs: {', '.join(invalid_characters)} passed."
                self.add_additional_system_message(content=error_message)
                async for update in self.stream_update(tool_call_id, "tool_error", error_message, tool_icon_error):
                    yield update
                return

            dialogue_job = await self._generate_scene_dialogue(tool_input)
            audio_segments = await self.generate_audio_segments(tool_input, dialogue_job["dialogue"])

            # Generate audio segments
            new_audio_segments = []
            for idx, segment_data in enumerate(audio_segments):
                audio_segment = AudioSegment(**segment_data)
                audio_segment.scene_index = tool_input.scene_index
                audio_segment.position_in_scene = idx
                new_audio_segments.append(audio_segment)
                async for update in self.stream_update(tool_call_id, "new_voice_recording", segment_data):
                    yield update

            # Add all new segments to the session at once
            self.agent_session.audio_segments.extend(new_audio_segments)

            # Reindex all segments after all have been added
            self.agent_session.reindex_all_segments()

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(
                content=f"Dialogue for scene #{tool_input.scene_index} generated successfully.")
            self.add_additional_system_message(
                content=(
                    "The dialogue for the scene has been generated successfully. "
                    "Audio segments have been automatically added to the media player for the user to listen to. "
                    "Please proceed with the next scene or finish the audio content creation if all scenes have been created."
                )
            )

            # Update the status of the scene to 'generated'
            if self.agent_session.content_outline and "scenes" in self.agent_session.content_outline:
                for scene in self.agent_session.content_outline["scenes"]:
                    if scene["scene_index"] == tool_input.scene_index:
                        scene["status"] = "generated"
                        break
                
            # Save the updated session
            self.agent_session.save()

            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Generated dialogue for scene #{tool_input.scene_index} successfully.",
                                                   tool_icon_successful):
                yield update
        except Exception as e:
            logging.error(f"Error generating scene dialogue: {str(e)}")
            logging.error(traceback.format_exc())

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Error generating scene dialogue: {str(e)}")
            self.add_additional_system_message(
                content="Explain why the scene dialogue generation failed and provide guidance on how to proceed.")
            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   f"Failed to generate dialogue for scene #{tool_input.scene_index} due to an internal error.",
                                                   tool_icon_error):
                yield update

            if self.agent_session.content_outline and "scenes" in self.agent_session.content_outline:
                for scene in self.agent_session.content_outline["scenes"]:
                    if scene["scene_index"] == tool_input.scene_index:
                        scene["status"] = "failed"
                        break
                
            # Save the updated session
            self.agent_session.save()

            # Yield the error as the final update
            yield {"type": "tool_error", "content": str(e)}

    def _validate_characters(self, character_ids: List[str]) -> List[str]:
        invalid_characters = []
        for char_id in character_ids:
            if char_id != "music_and_sound_effects" and not any(c.character_id == char_id for c in self.agent_session.characters_created):
                invalid_characters.append(char_id)
        return invalid_characters