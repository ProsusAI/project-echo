from enum import Enum

class OCRDocumentType(Enum):
    """
    Enum for document types to be used in optical_character_recognition
    """
    PDF = "pdf"
    IMAGE = "image"