import datetime
import uuid

from mongoengine import EmbeddedDocument, StringField, DateTimeField, BooleanField


class Character(EmbeddedDocument):
    character_id = StringField(default=lambda: str(uuid.uuid4())) # UUID
    name = StringField(required=True)
    role = StringField()
    description = StringField()
    personality = StringField()
    voice_id = StringField()
    is_fictional = BooleanField()
    photo_url = StringField()
    introduction_audio_url = StringField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    shared_with_user = BooleanField(default=False)
    background_colour = StringField()
