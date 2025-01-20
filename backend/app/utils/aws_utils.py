import io
import logging
import mimetypes
import traceback
from io import BytesIO
from typing import Optional

import boto3
from PIL import Image
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import get_settings
from app.core.factories.DocumentLoaderFactory.Factory import DocumentLoaderFactory
from app.utils.common_utils import resize_image

S3_BUCKET_NAME = get_settings().s3_bucket_name
S3_KEY_TEMPLATE = "{demo_name}/{session_id}/{filename}"
s3_client = boto3.client("s3")

logger = logging.getLogger(__name__)


def create_presigned_url(bucket_name: str, s3_key: str,
                         expiration: int = 3600,
                         use_http_get_method: bool = True) -> Optional[str]:
    """
    Creates a presigned URL for an object in S3

    :param bucket_name: the bucket name
    :param s3_key: the s3 key
    :param expiration: the expiration time in seconds
    :return: the presigned URL or None if error
    """
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name,
                    "Key": s3_key,
                    "ResponseCacheControl": f"private, max-age={expiration}, immutable"},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logger.error(e)
        return None

    return response


def create_presigned_url_for_upload(bucket_name: str, s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Creates a presigned URL for an object in S3 that can be used to upload a file

    :param bucket_name: the bucket name
    :param s3_key: the s3 key
    :param expiration: the expiration time in seconds
    :return: the presigned URL or None if error
    """
    try:
        response = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket_name, "Key": s3_key},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logging.error(e)
        return None

    return response


async def upload_bytes_to_s3(file_data: BytesIO, bucket_name: str, s3_key: str) -> None:
    """
    Uploads bytes to S3 with an automatically determined content type.

    :param file_data: the bytes to upload
    :param bucket_name: the bucket name
    :param s3_key: the s3 key
    :return: None
    """

    # Guess the MIME type of the file based on its extension
    content_type, _ = mimetypes.guess_type(s3_key)

    # If content_type is None, guess_type couldn't determine it, use 'binary/octet-stream' as default
    if content_type is None:
        content_type = 'binary/octet-stream'

    s3 = boto3.client("s3")
    # Add the ContentType parameter to set the guessed (or default) MIME type
    s3.upload_fileobj(
        BytesIO(file_data.getvalue()),
        bucket_name,
        s3_key,
        ExtraArgs={'ContentType': content_type}
    )


async def upload_bytes_to_s3_and_create_urls(file_bytes: bytes,
                                             demo_name: str,
                                             session_id: str,
                                             output_filename: str) -> (str, str):
    """
    Upload file bytes to S3 and create a URL
    :param file_bytes: the file bytes to upload
    :param demo_name: the demo name
    :param session_id: the session id
    :param output_filename: the name of the output file
    :return: the URL
    """
    file_bytes = BytesIO(file_bytes)
    output_s3_key = S3_KEY_TEMPLATE.format(
        demo_name=demo_name,
        session_id=session_id,
        filename=output_filename,
    )

    await upload_bytes_to_s3(
        file_data=file_bytes,
        bucket_name=S3_BUCKET_NAME,
        s3_key=output_s3_key,
    )

    # Create a short URL and slack formatted link
    file_presigned_url = create_presigned_url(
        S3_BUCKET_NAME, output_s3_key, expiration=3600
    )

    return file_presigned_url.replace("/minio:", "/localhost:").replace("host.docker.internal", "localhost").replace("/None/", "/")


def save_image_to_s3(generated_image: Image, image_s3_key: str) -> None:
    """
    Save the image to S3
    :param generated_image: the image to save
    :param image_s3_key: the key of the image
    :return: None
    """
    # Check images extension support alpha channel
    image_s3_key_extension = image_s3_key.split(".")[-1].lower()
    if image_s3_key_extension in ["png", "webp"] and generated_image.width < 16_384 and generated_image.height < 16_384:
        generated_image_format = "webp"
        quality = 100
    else:
        generated_image_format = "jpeg"
        quality = 80

    # Convert the image to RGB if it is RGBA
    if generated_image_format == "jpeg":
        generated_image = generated_image.convert("RGB")
    else:
        generated_image = generated_image.convert("RGBA")

    # Save the image as webp
    with io.BytesIO() as output:
        generated_image.save(output, format=generated_image_format, quality=quality)
        output.seek(0)
        s3_client.upload_fileobj(output, S3_BUCKET_NAME, image_s3_key)


def get_image_from_s3(image_s3_key: str) -> Image.Image:
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=image_s3_key)
    return Image.open(response["Body"])


def resize_and_replace_image(image_s3_key: str, limit_resize_to_max: bool = False) -> None:
    """
    Replace an image on S3 with a new compressed version of that image.
    :param image_s3_key: The S3 key of the image to be replaced
    :param limit_resize_to_max: Whether to limit the resize to the max width and height
    """
    # Download the image from S3
    image = get_image_from_s3(image_s3_key)
    resized_image = resize_image(image=image, limit_resize_to_max=limit_resize_to_max)

    # Save the image to S3
    save_image_to_s3(resized_image, image_s3_key)


def download_file_as_bytes_from_s3(s3bucket: str, file_s3_key: str) -> bytes:
    """
    Downloads an image from S3
    :param s3bucket: the bucket
    :param file_s3_key: the s3 key of the image to download
    :return: the image bytes
    """

    with io.BytesIO() as output:
        boto3.client("s3").download_fileobj(s3bucket, file_s3_key, output)
        output.seek(0)
        return output.read()


def extract_text_from_bytes(file_type: str, text_file_as_bytes: bytes) -> str:
    import magic
    mime_type = magic.from_buffer(text_file_as_bytes, mime=True).split("/")[0]
    file_loader = DocumentLoaderFactory.get_loader(
        file_type=file_type, mime_type=mime_type
    )
    try:
        file_content = file_loader.extract_text(text_file_as_bytes)
    except Exception as e:
        logger.error(f"Error extracting text from {file_type} and mime type {mime_type}: {e}")
        logger.error(traceback.format_exc())
        file_content = f"Failed to extract text from the file because of the following error: {e}"
    return file_content