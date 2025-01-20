from app.models.document_model import OCRDocumentType
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.AbstractDocumentLoader import (
    DocumentLoader,
)
import io
import logging
import os
from io import BytesIO
from typing import Union, Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def pdf_text_extractor(file_data: Union[bytes, io.BytesIO]) -> Optional[str]:
    try:
        if isinstance(file_data, bytes):
            pdf_reader = PdfReader(io.BytesIO(file_data))
        elif isinstance(file_data, io.BytesIO):
            file_data.seek(0)  # Reset stream pointer to the beginning
            pdf_reader = PdfReader(file_data)
        else:
            logger.error(f"Unsupported file type: {type(file_data).__name__}")
            return None

        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text is not None:
                text += page_text + "\n"

        return text.strip()
    except Exception as e:
        logger.exception(f"Failed to extract text from PDF, {e}")
        raise Exception("Failed to extract text from PDF, got error: " + str(e))
    
class PDFLoader(DocumentLoader):
    file_types = ["pdf"]
    mime_types = None

    def extract_text(self, content: bytes) -> str:
        text = pdf_text_extractor(content)

        if not text:
            raise Exception("No text found in PDF")
        
        return text

