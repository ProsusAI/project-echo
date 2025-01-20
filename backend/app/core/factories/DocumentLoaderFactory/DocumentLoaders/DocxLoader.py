import io

import docx

from app.core.factories.DocumentLoaderFactory.DocumentLoaders.AbstractDocumentLoader import (
    DocumentLoader,
)


class DocxLoader(DocumentLoader):
    file_types = ["docx"]
    mime_types = ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

    def extract_text(self, content: bytes) -> str:
        doc = docx.Document(io.BytesIO(content))
        return " ".join(para.text for para in doc.paragraphs)
