import httpx
import base64
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException
from openai import OpenAI, AsyncOpenAI
from app.config import get_settings


class StableDiffusionModel(str, Enum):
    ULTRA = "ultra"
    CORE = "core"
    SD3 = "sd3"

class OutputFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"

class AspectRatio(str, Enum):
    """Stable Diffusion Models"""
    SQUARE = "1:1"
    PORTRAIT = "2:3"
    LANDSCAPE = "3:2"
    WIDESCREEN = "16:9"
    ULTRAWIDE = "21:9"
    VERTICAL = "9:16"
    ULTRAVERTICAL = "9:21"
    GOLDEN = "4:5"
    GOLDEN_REVERSE = "5:4"

class ImageGenerationParams(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    model: StableDiffusionModel = Field(default=StableDiffusionModel.CORE)
    output_format: OutputFormat = Field(default=OutputFormat.PNG)
    aspect_ratio: AspectRatio = Field(default=AspectRatio.SQUARE)
    negative_prompt: Optional[str] = Field(default=None, max_length=10000)
    seed: Optional[int] = Field(default=None, ge=0, le=4294967294)

class StableDiffusionGenerator:
    BASE_URL = "https://api.stability.ai/v2beta/stable-image/generate"

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
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "image/*",
        }

    def _get_data(self, params: ImageGenerationParams):
        data = {
            "prompt": params.prompt,
            "output_format": params.output_format.value,
            "aspect_ratio": params.aspect_ratio.value,
        }
        if params.negative_prompt:
            data["negative_prompt"] = params.negative_prompt
        if params.seed is not None:
            data["seed"] = params.seed
        return data

    async def generate_image_async(self, params: ImageGenerationParams) -> bytes:
        url = f"{self.BASE_URL}/{params.model.value}"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = await self.async_client.post(url, headers=headers, data=data, files={"none": ''})
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    def generate_image(self, params: ImageGenerationParams) -> bytes:
        url = f"{self.BASE_URL}/{params.model.value}"
        headers = self._get_headers()
        data = self._get_data(params)

        try:
            response = self.sync_client.post(url, headers=headers, data=data, files={"none": ''})
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            self._raise_http_exception(e.response.status_code, str(e))
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

    @staticmethod
    def _raise_http_exception(status_code: int, error_detail: str):
        error_mapping = {
            400: ("Bad Request", "Invalid parameters"),
            403: ("Forbidden", "Content moderation flagged the request"),
            413: ("Request Entity Too Large", "Request too large"),
            422: ("Unprocessable Entity", "Unprocessable entity"),
            429: ("Too Many Requests", "Rate limit exceeded"),
            500: ("Internal Server Error", "Internal server error"),
        }
        error_type, default_message = error_mapping.get(status_code, ("Unknown Error", "An unknown error occurred"))
        raise HTTPException(status_code=status_code, detail=f"{error_type}: {error_detail or default_message}")


class DalleImageGeneration():

    def __init__(self):
        settings = get_settings()
        self.model = settings.openai_image_model
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.async_openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        if self.model == "dall-e-3":
            self.image_size = "1024x1024"
        elif self.model == "dall-e-2":
            self.image_size = "256x256"
        else:
            raise ValueError(f"Invalid model: {self.model}")

    def generate_image(self, params: ImageGenerationParams) -> bytes:
        response = self.openai_client.images.generate(
            model=self.model,
            prompt=params.prompt,
            size=self.image_size,
            response_format="b64_json",
        )
        
        image_bytes = base64.b64decode(response.data[0].b64_json)
        return image_bytes


    async def generate_image_async(self, params: ImageGenerationParams) -> bytes:
        response = await self.async_openai_client.images.generate(
            model=self.model,
            prompt=params.prompt,
            size=self.image_size,
            response_format="b64_json",
        )

        image_bytes = base64.b64decode(response.data[0].b64_json)
        return image_bytes


class ImageGeneration:
    def __init__(self):
        if get_settings().stability_api_key:
            self.mode = "stable_diffusion"
            self.generator = StableDiffusionGenerator(get_settings().stability_api_key)
        else:
            self.mode = "dalle"
            self.generator = DalleImageGeneration()

    def generate_image(self, params: ImageGenerationParams) -> bytes:
        return self.generator.generate_image(params)

    async def generate_image_async(self, params: ImageGenerationParams) -> bytes:
        if self.mode == "stable_diffusion":
            with self.generator as generator:
                return await generator.generate_image_async(params)
        else:
            return await self.generator.generate_image_async(params)
