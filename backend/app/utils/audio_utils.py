import asyncio
import io
import logging
import tempfile
import zipfile

import aiohttp
from pydub import AudioSegment

from app.models.audio_segment_model import AudioSegment as InternalAudioSegment

logger = logging.getLogger(__name__)


async def download_audio_segment(session, segment: InternalAudioSegment):
    url = segment.audio_segment_url.replace("/localhost:", "/minio:")
    async with session.get(url) as response:
        if response.status == 200:
            content = await response.read()
            audio = AudioSegment.from_mp3(io.BytesIO(content))
            return audio
        else:
            logger.error(f"Failed to download segment {segment['segment_index']}")
            return None


async def download_audio_segments(segments: list[InternalAudioSegment]):
    async with aiohttp.ClientSession() as session:
        tasks = [download_audio_segment(session, segment) for segment in segments]
        return await asyncio.gather(*tasks)


def stitch_audio_segments(audio_segments: list[AudioSegment]):
    combined = audio_segments[0]
    for segment in audio_segments[1:]:
        if segment is not None:
            combined += segment
    return combined


def create_srt_content(segments: list[InternalAudioSegment]):
    srt_content = ""
    current_time = 0.0
    for segment in segments:
        start_time = current_time
        end_time = current_time + segment['duration']
        start_time_str = format_srt_time(start_time)
        end_time_str = format_srt_time(end_time)
        srt_content += f"{segment['segment_index'] + 1}\n"
        srt_content += f"{start_time_str} --> {end_time_str}\n"
        srt_content += f"{segment['segment_text']}\n\n".replace("🎶", "").replace("🎵", "")
        current_time = end_time
    return srt_content


def format_srt_time(seconds: float):
    millis = int((seconds % 1) * 1000)
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def zip_audio_and_srt(audio_data: bytes, srt_content: str):
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip_file:
        with zipfile.ZipFile(temp_zip_file.name, 'w') as zf:
            # Add audio file to the zip
            zf.writestr("output.mp3", audio_data)

            # Add SRT file to the zip
            zf.writestr("output.srt", srt_content)

        # Read the zip file contents into bytes
        with open(temp_zip_file.name, 'rb') as f:
            zip_data = f.read()

    return zip_data
