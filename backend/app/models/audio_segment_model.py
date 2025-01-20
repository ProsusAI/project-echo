import datetime

from mongoengine import EmbeddedDocument, StringField, DateTimeField, BooleanField, IntField, DictField, FloatField


class AudioSegment(EmbeddedDocument):
    segment_index = IntField(required=True)
    segment_text = StringField(required=True)
    audio_segment_url = StringField(required=True)
    character_id = StringField(required=True)
    character_name = StringField(required=True)
    character_photo_url = StringField(required=True)
    character_colour = StringField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    shared_with_user = BooleanField(default=False)
    alignment_info = DictField(required=False, null=True)
    duration = FloatField(required=False, null=True)
    scene_index = IntField(required=True, description="The index of the scene this segment belongs to.")
    position_in_scene = IntField(required=True, description="The position of this segment within the scene.")

    meta = {
        'indexes': [
            {'fields': ('scene_index', 'position_in_scene'), 'unique': True}
        ]
    }
