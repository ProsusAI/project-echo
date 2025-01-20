from abc import ABC, abstractmethod


class DocumentLoader(ABC):
    """
    Implement this abstract class and add to get_all_loaders() function in Factory.py to add a new document loader
    You can set file_types to a list of file types which a file can have so that this loader is triggered.
    mime_types can be set to a list of partial mime types so that if a partial mime type is in the full mime
        type of a file, this loader is triggered.
    """

    file_types = None
    mime_types = None

    @abstractmethod
    def extract_text(self, content: bytes) -> str:
        """
        Function to extract text from a file.
        :param content: bytes content of the file for which text needs to be extracted
        :return: text content of file
        """
        raise NotImplementedError()
    
        
    def loader_uses_ocr(self) -> bool:
        return False
