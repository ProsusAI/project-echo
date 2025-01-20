import io
import logging
import os
from io import BytesIO
from typing import Union, Optional

import PIL
from PIL import Image
from azure.ai.formrecognizer import FormRecognizerClient, DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ODataV4Format
from pypdf import PdfReader

from app.models.document_model import OCRDocumentType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")

AZURE_OCR_MIN_IMAGE_WIDTH = 50
AZURE_OCR_MIN_IMAGE_HEIGHT = 50
AZURE_OCR_MAX_IMAGE_WIDTH = 10000
AZURE_OCR_MAX_IMAGE_HEIGHT = 10000


def try_image_to_png(file: bytes) -> Union[None, bytes]:
    try:
        return image_to_png(file)
    except Exception:
        logging.exception(f"Failed to convert bytes to png")
        return None


def image_to_png(file: bytes) -> bytes:
    out = BytesIO()
    img = Image.open(BytesIO(file))
    img.save(out, "PNG")
    out.seek(0)
    return out.read()


def add_margin(pil_img, top, right, bottom, left, color):
    width, height = pil_img.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(pil_img.mode, (new_width, new_height), color)
    result.paste(pil_img, (left, top))
    return result


def pad_pil_image_to_min_size(
        img: Image,
        min_width: int = AZURE_OCR_MIN_IMAGE_WIDTH,
        min_height: int = AZURE_OCR_MIN_IMAGE_HEIGHT,
) -> Image:
    min_height = min_height or AZURE_OCR_MIN_IMAGE_HEIGHT
    min_width = min_width or AZURE_OCR_MIN_IMAGE_WIDTH

    cur_width, cur_height = img.size
    if cur_width >= min_width and cur_height >= min_height:
        return img

    target_width = max(cur_width, min_width)
    target_height = max(cur_height, min_height)
    logger.info(f"Resizing image to W:{target_width} H:{target_height}")

    img = add_margin(
        img,
        top=0, right=0,
        bottom=target_width - cur_width,
        left=target_height - cur_height,
        color=0,  # black
    )
    return img


def pil_image_to_bytes(img: Image, target_format: str) -> bytes:
    out = BytesIO()
    img.save(out, target_format)
    out.seek(0)
    return out.read()


def crop_pil_image_to_max_size(img: Image, max_width: int, max_height: int):
    cur_width, cur_height = img.size
    target_width = min(cur_width, max_width)
    target_height = min(cur_height, max_height)
    logger.info(f"Cropping image to W:{target_width} H:{target_height}")
    img = img.crop((0, 0, target_width, target_height))
    return img


def normalize_image_bytes_for_ocr(
        file: bytes,
        min_width: int = AZURE_OCR_MIN_IMAGE_WIDTH,
        min_height: int = AZURE_OCR_MIN_IMAGE_HEIGHT,
        max_width: int = AZURE_OCR_MAX_IMAGE_WIDTH,
        max_height: int = AZURE_OCR_MAX_IMAGE_HEIGHT,
) -> dict:
    img = Image.open(BytesIO(file))
    img_format = img.format
    cur_width, cur_height = img.size
    if cur_width < min_width or cur_height < min_height:
        img = pad_pil_image_to_min_size(img, min_width=min_width, min_height=min_height)
        file = pil_image_to_bytes(img, img_format)
    if cur_width > max_width or cur_height > max_height:
        img = crop_pil_image_to_max_size(img, max_width=max_width, max_height=max_height)
        file = pil_image_to_bytes(img, img_format)

    width, height = img.size
    return {
        "bytes": file,
        "format": img_format,
        "width": width,
        "height": height,
    }


def optical_character_recognition(file: bytes, document_type: str) -> str:
    """
    Given a file, perform OCR and return the transcription text
    :param file: bytes
    :param document_type: a value in OCRDocumentType
    :return: str
    """

    # Handle text rich content (pdf) differently then normal images
    if document_type == OCRDocumentType.PDF.value:
        return pdf_to_text_using_ocr(file)

    elif document_type == OCRDocumentType.IMAGE.value:
        return image_to_text_using_ocr(file)
    else:
        logger.exception(
            f"optical_character_recognition called with invalid document_type",
            extra={"document_type": document_type},
        )
        return f"optical_character_recognition called with invalid document_type: {document_type}"


def image_to_text_using_ocr(file: bytes) -> str:
    """Use OCR to extract text from image"""

    try:
        # Create a Form Recognizer client
        client = FormRecognizerClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))
    except Exception:
        logger.exception("Couldn't create Azure FormRecognizerClient")
        return ""

    # Image needs normalization
    try:
        normalized_image = normalize_image_bytes_for_ocr(file)
    except PIL.UnidentifiedImageError:
        logger.warning("Couldn't interpret the image", exc_info=True)
        return ""
    except Exception:
        logger.exception("Couldn't normalize image for ocr", exc_info=True)
        return ""

    configurations = [{
        "name": "basic",
        "content_type": "image/" + normalized_image["format"].lower(),  # Azure is case-sensitive
        "preprocess": lambda x: x,

    }, {
        "name": "convert-to-png",
        "content_type": "image/png",
        "preprocess": try_image_to_png,
    }]

    # Try different OCR configurations
    for idx, cur_conf in enumerate(configurations, 1):

        cur_att_name = cur_conf.get("name", "__UNNAMED__")
        logger.info(f"Using OCR configuration {cur_att_name} - attempt {idx}/{len(configurations)}")

        # Preprocess file specific to configuration
        preprocessed_file = try_image_to_png(normalized_image["bytes"])

        try:
            # Recognize content
            poller = client.begin_recognize_content(
                preprocessed_file,
                content_type=cur_conf.get("content_type")
            ).result()

            # Extract text
            text = "".join(line.text + "\n" for page in poller for line in page.lines or [])
            return text

        except HttpResponseError as e:
            err = getattr(e, "error")
            if isinstance(err, ODataV4Format):
                logger.warning(f"Azure OCR returned HttpResponseError with error ODataV4Format", extra={
                    "configuration": cur_att_name,
                    "error_code": err.code,
                    "error_message": err.message_details(),
                })
            else:
                logger.exception(
                    f"Azure OCR returned an unexpected HttpResponseError",
                    extra={"configuration": cur_att_name})

            return ""
        except Exception:
            logger.warning(f"no text found in file", exc_info=True, extra={"configuration": cur_att_name})

    logger.exception(f"Failed to extract OCR after {len(configurations)} attempts")
    return ""


def pdf_to_text_using_ocr(file: bytes) -> str:
    """Use newest OCR to extract text from PDF"""

    # Content is pdf, so we need to use the DocumentAnalysisClient (v3.0)
    try:
        ocr_client = DocumentAnalysisClient(
            endpoint=AZURE_ENDPOINT,
            credential=AzureKeyCredential(AZURE_KEY)
        )
    except Exception:
        logger.exception("Couldn't create Azure DocumentAnalysisClient")
        return ""

    try:
        poller = ocr_client.begin_analyze_document(
            model_id="prebuilt-document",
            document=file,
        ).result()

        # Extract text -> Note: line has content not text
        return "".join(
            line.content + "\n" for page in poller.pages
            for line in page.lines or []
        )

    except HttpResponseError as e:
        err = getattr(e, "error")
        if isinstance(err, ODataV4Format):
            logger.warning(f"Azure OCR returned HttpResponseError with error ODataV4Format", extra={
                "configuration": 'pdf-OCR-azure',
                "error_code": err.code,
                "error_message": err.message_details(),
            })
        else:
            logger.exception(
                f"Azure OCR returned an unexpected HttpResponseError",
                extra={"configuration": 'pdf-OCR-azure'})

        return ""

    except Exception:
        logger.warning(f"no text found in file", exc_info=True, extra={"configuration": 'pdf-OCR-azure'})
        return "No text found in file"


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
        return None
