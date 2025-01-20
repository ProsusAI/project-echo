from app.models.document_model import OCRDocumentType
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.AbstractDocumentLoader import (
    DocumentLoader,
)
from app.utils.ocr_utils import optical_character_recognition


class ImageLoader(DocumentLoader):
    file_types = None
    mime_types = ["image"]

    def extract_text(self, content: bytes) -> str:
        return optical_character_recognition(content, document_type=OCRDocumentType.IMAGE.value)
    
    def loader_uses_ocr(self):
        return True
