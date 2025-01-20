from app.core.factories.DocumentLoaderFactory.DocumentLoaders.AbstractDocumentLoader import (
    DocumentLoader,
)


def decode_bytes(bytes_object):
    encodings = ['utf-8', 'ISO-8859-1', 'latin1', 'ascii']
    for encoding in encodings:
        try:
            return bytes_object.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise Exception("Failed to decode content")


class PlainTextLoader(DocumentLoader):
    file_types = None
    mime_types = ["text"]

    def extract_text(self, content: bytes):
        return decode_bytes(content)
