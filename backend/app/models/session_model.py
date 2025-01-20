import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
import boto3
import logging
import urllib.parse

from app.models.audio_segment_model import AudioSegment
from app.models.character import Character
from app.config import get_settings

from mongoengine import (
    Document,
    StringField,
    ListField,
    DictField,
    SequenceField,
    EmbeddedDocumentField,
    EmbeddedDocument,
    DateTimeField,
    signals
)

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3')

# Define the default character
default_character = Character(
    character_id=str(uuid.uuid4()),
    name="Greeting",
    role="Opening",
    description="Generates a suitable greeting for the audio content.",
    personality="Friendly, warm, and engaging voice.",
    voice_id="kPzsL2i3teMYv0FxEYQ6",
    is_fictional=True,
    photo_url="https://public-ai-voice-director-files.s3.eu-west-1.amazonaws.com/music_note.webp",
    introduction_audio_url="https://public-ai-voice-director-files.s3.eu-west-1.amazonaws.com/melody_character.mp3",
    created_at=datetime.utcnow(),
    shared_with_user=False,
    background_colour="white"
)

class SessionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    FAILED = "failed"
    WAITING_FOR_USER_INPUT = "waiting_for_user_input"

class MessageType(str, Enum):
    USER = "user"
    BOT = "bot"
    TOOL = "tool"
    FOLLOW_UP = "follow_up"

class DemoName(str, Enum):
    VOICE_DIRECTOR_V1 = "voice_director_v1"

class Message(EmbeddedDocument):
    id = StringField(default=str(uuid.uuid4()))
    message_type = StringField(choices=[message_type for message_type in MessageType])
    text = StringField(required=True, default='')
    timestamp = DateTimeField(default=datetime.utcnow)
    
    def to_mongo(self, *args, **kwargs):
        data = super().to_mongo(*args, **kwargs)
        # Ensure id is included in the output
        if '_id' in data and 'id' not in data:
            data['id'] = str(data.pop('_id'))
        return data

class UploadedFile(EmbeddedDocument):
    filename = StringField(required=True)
    s3_key = StringField(required=True)
    uploaded_datetime = DateTimeField(default=datetime.utcnow)
    short_url = StringField(null=True)

class Session(Document):
    id = SequenceField(primary_key=True)
    creation_datetime = DateTimeField(default=datetime.utcnow)
    last_update_datetime = DateTimeField(default=datetime.utcnow)
    status = StringField(choices=[status for status in SessionStatus], default=SessionStatus.PENDING)
    openai_messages = ListField(DictField(), default=[])
    demo_name = StringField(default=DemoName.VOICE_DIRECTOR_V1)
    messages = ListField(EmbeddedDocumentField(Message))
    characters_created = ListField(EmbeddedDocumentField(Character), default=[])
    audio_segments = ListField(EmbeddedDocumentField(AudioSegment), default=[])
    content_title = StringField(null=True)
    content_subtitle = StringField(null=True)
    user_uploaded_files = ListField(EmbeddedDocumentField(UploadedFile), default=[])
    user_info = DictField(null=True)
    content_outline = DictField(null=True)

    meta = {
        "collection": "session",
        "indexes": [
            "creation_datetime",
            "last_update_datetime",
            "status",
            "demo_name"
        ]
    }

    def _get_s3_keys_to_delete(self) -> list:
        """Collect all S3 keys that need to be deleted."""
        s3_keys = []
        
        def extract_s3_key(url: str) -> str:
            """Extract S3 key from either Minio or S3 presigned URL."""
            if not url:
                return None
                
            try:
                if '/minio:' in url:
                    # Handle Minio URLs
                    key = url.split('/minio:')[1].split('?')[0]
                    key = urllib.parse.unquote(key)
                    return key
                elif '.s3.' in url:
                    # Handle S3 presigned URLs
                    key = url.split('.com/')[1].split('?')[0]
                    key = urllib.parse.unquote(key)
                    return key
                logger.warning(f"URL does not match expected patterns: {url}")
                return None
            except Exception as e:
                logger.error(f"Error extracting S3 key from URL {url}: {str(e)}")
                return None
        
        # Add character files
        for character in self.characters_created:
            if character.photo_url:
                s3_key = extract_s3_key(character.photo_url)
                if s3_key:
                    s3_keys.append(s3_key)
            if character.introduction_audio_url:
                s3_key = extract_s3_key(character.introduction_audio_url)
                if s3_key:
                    s3_keys.append(s3_key)

        # Add audio segments
        for segment in self.audio_segments:
            if segment.audio_segment_url:
                s3_key = extract_s3_key(segment.audio_segment_url)
                if s3_key:
                    s3_keys.append(s3_key)

        # Add uploaded files
        for file in self.user_uploaded_files:
            if file.s3_key:
                s3_keys.append(file.s3_key)

        # Remove duplicates and filter out None values
        s3_keys = list(set(filter(None, s3_keys)))

        # Filter out melody_character.mp3 and music_note.webp
        s3_keys = [key for key in s3_keys if key not in ['melody_character.mp3', 'music_note.webp']]
        
        return s3_keys

    def _delete_s3_files(self):
        """Delete all S3 files associated with this session."""
        s3_keys = self._get_s3_keys_to_delete()
        bucket_name = get_settings().s3_bucket_name

        for s3_key in s3_keys:
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
            except Exception as e:
                logger.error(f"Error deleting S3 object {s3_key}: {str(e)}")

    @classmethod
    def pre_delete(cls, sender, document, **kwargs):
        """Pre-delete hook to clean up S3 files before session deletion."""
        document._delete_s3_files()

    def add_message(self, message_type: MessageType, text: str) -> "Session":
        if self.messages and self.messages[-1].text == text:
            return self

        new_message = Message(message_type=message_type, text=text)
        self.messages.append(new_message)
        self.last_update_datetime = datetime.utcnow()
        self.save()
        return self

    async def load_conversation(self) -> "Session":
        """Load the conversation data for a session."""
        session = Session.objects(id=self.id).first()
        if not session:
            raise ValueError(f"Session {self.id} not found")

        self.messages = session.messages
        self.openai_messages = session.openai_messages
        self.characters_created = session.characters_created
        self.audio_segments = session.audio_segments
        self.content_title = session.content_title
        self.content_subtitle = session.content_subtitle
        self.content_outline = session.content_outline
        self.user_uploaded_files = session.user_uploaded_files
        self.last_update_datetime = datetime.utcnow()
        self.save()
        return self

    async def save_conversation(self) -> "Session":
        self.last_update_datetime = datetime.utcnow()
        self.save()
        return self

    def add_uploaded_file(self, filename: str, s3_key: str, short_url: str) -> "Session":
        new_uploaded_file = UploadedFile(filename=filename, s3_key=s3_key, short_url=short_url)
        self.user_uploaded_files.append(new_uploaded_file)
        self.last_update_datetime = datetime.utcnow()
        self.save()
        return self

    def remove_uploaded_file(self, filename: str) -> "Session":
        self.user_uploaded_files = [file for file in self.user_uploaded_files if file.filename != filename]
        self.last_update_datetime = datetime.utcnow()
        self.save()
        return self

    def get_character_by_id(self, character_id: str) -> Optional[Character]:
        return next((c for c in self.characters_created if c.character_id == character_id), None)

    def add_audio_segment(self, segment: AudioSegment):
        self.audio_segments.append(segment)

    def reindex_all_segments(self):
        from itertools import groupby
        from operator import attrgetter

        # Assign default position_in_scene if None
        for seg in self.audio_segments:
            if seg.position_in_scene is None:
                seg.position_in_scene = 0

        # Sort all segments first by scene_index, then by position_in_scene
        self.audio_segments.sort(key=lambda seg: (seg.scene_index, seg.position_in_scene))
        
        # Group segments by scene_index
        grouped_segments = groupby(self.audio_segments, key=attrgetter('scene_index'))
        
        global_index = 0
        for scene_index, segments_in_scene in grouped_segments:
            for segment in segments_in_scene:
                segment.segment_index = global_index
                global_index += 1
        
        self.save()

# Connect the pre_delete signal
signals.pre_delete.connect(Session.pre_delete, sender=Session)
