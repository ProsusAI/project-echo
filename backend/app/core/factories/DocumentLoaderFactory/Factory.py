from typing import Dict, List, Optional, Type

from app.core.factories.DocumentLoaderFactory.DocumentLoaders.AbstractDocumentLoader import (
    DocumentLoader,
)
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.DocxLoader import (
    DocxLoader,
)
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.PDFLoader import (
    PDFLoader,
)
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.PlainTextLoader import (
    PlainTextLoader,
)
from app.core.factories.DocumentLoaderFactory.DocumentLoaders.PptxLoader import (
    PptxLoader,
)


def get_all_loaders() -> List[Type[DocumentLoader]]:
    """
    Returns all document loaders
    """
    return [DocxLoader, PDFLoader, PlainTextLoader, PptxLoader]


def aggregate_loaders_to_map(
    loaders: List[Type[DocumentLoader]], property_name: str
) -> Dict[str, Type[DocumentLoader]]:
    """
    Aggregates all loaders into a dictionary map so that every key,
        listed as one of the values in property_name of a class,
        will refer to the class in which that key was found.
        This map can later be used to easily retrieve a loader based on either file type or mime type of a file.

    :param loaders: list of all possible document loader classes
    :param property_name: name of property of the class that needs to be considered
    :return: map from values to document loader classes
    """
    field_map = {}
    for loader in loaders:
        prop_value = getattr(loader, property_name)

        if prop_value is not None:
            for value in prop_value:
                if value in field_map:
                    raise Exception(
                        f"Double {property_name} match, type {value} occurred twice in classes {loader} & {field_map[value]}"
                    )

                field_map[value] = loader

    return field_map


def get_loader_from_mime(file_mime_type: str) -> Optional[DocumentLoader]:
    """
    Returns an instance of a document loader based on a files mimetype
    """
    loaders = get_all_loaders()
    mime_type_map = aggregate_loaders_to_map(loaders, "mime_types")

    for mime_type, cls in mime_type_map.items():
        if mime_type in file_mime_type:
            return cls()

    return None


def get_loader_from_filetype(file_type: str) -> Optional[DocumentLoader]:
    """
    Returns an instance of a document loader based on a files file type
    """
    loaders = get_all_loaders()
    type_map = aggregate_loaders_to_map(loaders, "file_types")

    loader_class = type_map.get(file_type, None)

    if loader_class is None:
        return None

    return loader_class()


class DocumentLoaderFactory:
    """
    Factory that loads a correct document loader based on file type and mime type.
    Factory first tries to match file type. If no match is found a mime type is tried to be matched.
    All document loaders returned from function get_all_loaders are considered.
    """

    @staticmethod
    def get_loader(file_type: str, mime_type: str) -> Optional[DocumentLoader]:
        """
        Returns loader based on file type and mime type

        :param file_type: file type
        :param mime_type: mime type
        :return: an instance of a Document Loader
        """
        loader = get_loader_from_filetype(file_type) or get_loader_from_mime(mime_type)

        if loader is None:
            return None

        return loader
