import base64
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from app.config import get_settings
from openai import OpenAI, AsyncOpenAI
import json
import logging
import traceback
import httpx
from fastapi import HTTPException


# Making ElevenLabs voices to OpenAI voices
convert_voice_id_to_name = {
    "nova": {
        "nDJIICjR9zfJExIFeSCN": "Youthful British voice of Emmaline, perfect for fairy tales.",
        "kPzsL2i3teMYv0FxEYQ6": "Young, vibrant female voice, ideal for celebrity news, hot topics, and fun social media.",
        "xctasy8XvGp2cVO9HL9k": "Fun millennial female voice, perfect for news, commercials, audiobooks, and relatable content.",
    },
    "shimmer": {
        "Xb7hH8MSUJpSbSDYk0k2": "Middle-aged British female voice, ideal for documentaries, audiobooks, and news.",
    },
    "alloy":{
        "7NsaqHdLuKNFvEfjpUno": "Voice of an old wise seer woman, ideal for fantasy and mystery genres.",
    },
    "sage": {
        "aTxZrSrp47xsP6Ot4Kgd": "Urban American female voice, ideal for casual conversations, podcasts, and social media.",
        "CBHdTdZwkV4jYoCyMV1B": "African American female voice with a friendly and engaging tone, great for casual or animated characters.",
    },
    "coral": {
        "IrrK2GZCVzp6blf6N0K9": "Old British female voice, aristocratic and posh, suitable for vintage tones.",
        "XCu2eL1emctKKTC2nbsu": "Well-spoken and professional woman with an inquisitive voice. (suitable for old women (80+ years old), witches in stories)",
    },
    "ash": {
        "5yILjDb8nNabml6pQhwj": "Conversational warm and resonant American male voice, moderate to slow diction.",
        "pqHfZKP75CvOlQylNhV4": "Young American male voice, great for health nutrition videos.",
        "tlETan7Okc4pzjD0z62P": "Well-spoken Arabic & Middle East male voice, suitable for conversational, audiobooks, social media, and news.",
    "onyx":{
        "raMcNf2S8wCmuaBcyI6E": "Pleasant middle-aged American voice for narration, explainer videos, and eLearning.",
        "bPMKpgEe88vKSwusXTMU": "Warm and confident American male voice, perfect for storytelling.",
        "WNPU2f2Gr5PpDLI9wPbq": "Professional American male voice with a calm tone, suitable for health, fitness, and wellness.",
    },
    },
    "echo":{
        "dpe9OBKZEK1BHfVjZ1n2": "Middle-aged American-Irish-British male with a clear, confident voice, suitable for documentaries, audiobooks, and news.",
        "yl2ZDV1MzN4HbQJbMihG": "Upbeat and pleasant male voice, great for YouTube, shorts, and social media.",
    },
    "fable": {
        "NFG5qt843uXKj4pFvR7C": "Middle-aged Brit with a velvety, laid-back, late-night talk show host timbre.",
    },
}

voices_to_gender = {
    "female": "nova",
    "male": "ash"
}


class OpenAIAudioParams(BaseModel):
    """
    Holds parameters for requesting text and audio from OpenAI's audio-enabled models.
    """
    text: str = Field(..., description="The text you like to convert to audio.")
    voice_id: str = Field(..., description="Voice ID to use for audio generation.")

def create_audio_system_prompt(params: OpenAIAudioParams) -> Tuple[str, str]:
    voice_id = params.voice_id
    voice_type = ''
    
    for voice, voice_ids in convert_voice_id_to_name.items():
        if voice_id in voice_ids:
            voice_explanation = voice_ids[voice_id]
            voice_type = voice
            break
        
    voice_explanation = voice_explanation.strip(".")
    instructions = f"""You are an advanced AI voice generator capable of producing highly customizable audio output. Your task is to read the provided text with specific vocal characteristics. Follow these guidelines meticulously:

1. Content Accuracy:
   - Read ONLY the exact text provided. Do not add, remove, or modify any words.
   - End your speech immediately after the last word of the provided text.

2. Voice:
   - Use the voice of a '{voice_explanation}' to read the text.

6. Pauses and Emphasis:
   - Use brief, natural pauses between sentences for clarity.
   - Emphasize key words or phrases to enhance understanding and engagement.

7. Consistency:
   - Maintain consistency in your chosen vocal characteristics throughout the delivery.
   - Ensure smooth transitions between different emotional tones if required.

Remember: Your primary goal is to deliver the exact provided text with the specified vocal characteristics. Do not deviate from the content while applying these audio parameters."""

    return instructions, voice_type

class OpenAITTSGenerator:
    """
    A class similar in structure to ElevenLabsTTSGenerator, but refactored
    for OpenAI's audio preview features. 
    """

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_audio_model

    def generate_speech(self, params: OpenAIAudioParams) -> bytes:
        """
        Synchronously generate audio (and text) from the model.
        Returns wave bytes that you can write to a WAV file.
        """
        system_prompt, voice_type = create_audio_system_prompt(params)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": params.text}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            modalities=["audio"],
            audio={"voice": voice_type, "format": "mp3"},
            messages=messages
        )

        # data[string]
        #  Base64 encoded audio bytes generated by the model, in the format specified in the request.
        audio_base64 = response.choices[0].message.audio.data
        audio_bytes = base64.b64decode(audio_base64)

        return {
            "audio_bytes": audio_bytes,
            "alignment_dict": {}
        }

    async def generate_speech_async(self, params: OpenAIAudioParams) -> bytes:
        """
        Asynchronously generate audio (and text).
        Depending on the OpenAI client you're using, the async usage might vary.
        You could adapt this for an async-literate version of the library.
        """
        system_prompt, voice_type = create_audio_system_prompt(params)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": params.text}
        ]

        response = await self.async_client.chat.completions.create(
            model=self.model,
            modalities=["text", "audio"],
            audio={"voice": voice_type, "format": "mp3"},
            messages=messages
        )

        # data[string]
        #  Base64 encoded audio bytes generated by the model, in the format specified in the request.
        audio_base64 = response.choices[0].message.audio.data
        audio_bytes = base64.b64decode(audio_base64)

        return {
            "audio_bytes": audio_bytes,
            "alignment_dict": {}
        }




logger = logging.getLogger(__name__)


class VoiceSettings(BaseModel):
    stability: float = Field(0.5, ge=0, le=1)
    similarity_boost: float = Field(0.8, ge=0, le=1)
    style: float = Field(0.0, ge=0, le=1)
    use_speaker_boost: bool = True


class PronunciationDictionaryLocator(BaseModel):
    pronunciation_dictionary_id: str
    version_id: Optional[str] = None


class TTSParams(BaseModel):
    text: str
    voice_id: str = "kPzsL2i3teMYv0FxEYQ6"
    model_id: str = "eleven_turbo_v2_5"
    language_code: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None
    pronunciation_dictionary_locators: Optional[List[PronunciationDictionaryLocator]] = None
    seed: Optional[int] = None
    previous_text: Optional[str] = None
    next_text: Optional[str] = None
    previous_request_ids: Optional[List[str]] = None
    next_request_ids: Optional[List[str]] = None


class SoundGenerationParams(BaseModel):
    text: str
    duration_seconds: int


class ElevenLabsTTSGenerator:
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.async_client = httpx.AsyncClient(timeout=60)
        self.sync_client = httpx.Client(timeout=60)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.async_client.aclose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_client.close()

    def _get_headers(self):
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _get_data(self, params: BaseModel) -> Dict:
        return params.dict(exclude_none=True)

    async def generate_speech_async(self, params: TTSParams) -> dict:
        url = f"{self.BASE_URL}/text-to-speech/{params.voice_id}/with-timestamps"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = await self.async_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            json_string = await response.aread()
            response_dict = json.loads(json_string)
            audio_bytes = base64.b64decode(response_dict["audio_base64"])
            return {
                "audio_bytes": audio_bytes,
                "alignment_dict": response_dict["alignment"],
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response from ElevenLabs: {e.response.text}")
            logger.error(traceback.format_exc())
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            logger.error(f"Error response from ElevenLabs: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    def generate_speech(self, voice_id: str, params: TTSParams) -> bytes:
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}/stream"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = self.sync_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    async def generate_sound_async(self, params: SoundGenerationParams) -> dict:
        url = f"{self.BASE_URL}/sound-generation"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = await self.async_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return {
                "audio_bytes": response.content,
                "alignment_dict": {},
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Error response from ElevenLabs: {e.response.text}")
            logger.error(traceback.format_exc())
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            logger.error(f"Error response from ElevenLabs: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    def generate_sound(self, params: SoundGenerationParams) -> dict:
        url = f"{self.BASE_URL}/sound-generation"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = self.sync_client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    @staticmethod
    def _raise_http_exception(status_code: int, error_detail: str):
        error_mapping = {
            400: ("Bad Request", "Invalid parameters"),
            401: ("Unauthorized", "Invalid API key"),
            403: ("Forbidden", "Insufficient permissions"),
            404: ("Not Found", "Resource not found"),
            429: ("Too Many Requests", "Rate limit exceeded"),
            500: ("Internal Server Error", "Server error occurred"),
        }
        error_type, default_message = error_mapping.get(status_code, ("Unknown Error", "An unknown error occurred"))
        raise HTTPException(status_code=status_code, detail=f"{error_type}: {error_detail or default_message}")



class TTSGenerator:
    """
    A class that generates audio using either ElevenLabs or OpenAI.
    Depending on the available API keys. We also support kokoro model.
    We recommend using: https://github.com/remsky/Kokoro-FastAPI
    """

    def __init__(self):
        self.settings = get_settings()
        self.mode = ""

        if self.settings.elevenlabs_api_key:
            self.generator = ElevenLabsTTSGenerator(api_key=self.settings.elevenlabs_api_key)
            self.mode = "elevenlabs"
        elif self.settings.kokoro_base_url:
            self.generator = OpenAITTSGenerator()
            self.client = OpenAI(
                base_url=self.settings.kokoro_base_url,
                api_key="not-needed"
            )
            self.async_client = AsyncOpenAI(
                base_url=self.settings.kokoro_base_url,
                api_key="not-needed"
            )
            self.mode = "openai"
        else:
            self.generator = OpenAITTSGenerator()
            self.mode = "openai"

    def param_converter(self, params: TTSParams) -> TTSParams:
        if self.mode == "elevenlabs":
            return params
        else:
            return OpenAIAudioParams(text=params.text, voice_id=params.voice_id)

    def generate_speech(self, params: TTSParams) -> bytes:
        return self.generator.generate_speech(self.param_converter(params))
    
    async def generate_speech_async(self, params: TTSParams) -> bytes:
        return await self.generator.generate_speech_async(self.param_converter(params))

    def generate_sound(self, params: SoundGenerationParams) -> dict:
        if self.mode == "elevenlabs":
            return self.generator.generate_sound(params)
        else:
            raise ValueError("Sound generation is not supported for OpenAI mode")
    
    async def generate_sound_async(self, params: SoundGenerationParams) -> dict:
        if self.mode == "elevenlabs":
            return await self.generator.generate_sound_async(params)
        else:
            raise ValueError("Sound generation is not supported for OpenAI mode")
