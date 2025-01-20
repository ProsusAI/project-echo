import logging
import re
import uuid
from typing import Optional, Dict
from urllib.parse import unquote, urlparse

import requests
from pydantic import Field

from app.core.tool_executor.tools import AgentTool
from app.schemas.tool_model import ToolInput
from app.utils.url_content_extraction import extract_text_from_urls


class SaveUrlAsFileTool(AgentTool):
    @classmethod
    def schema(cls, replacements: Optional[Dict[str, str]] = None) -> dict:
        return cls.SaveUrlAsFile.get_schema(replacements)

    class SaveUrlAsFile(ToolInput):
        """Saves the content of an url to a file so that it can be used by other tools (e.g. summarization, question answering, etc.)"""
        url_to_save: str = Field(...,
                                 description="The url to save its content to a file")

    def _clean_url_title(self, url_title: str, url: str) -> Optional[str]:
        if not url_title:
            url_domain = urlparse(url).netloc
            url_domain = url_domain.replace("www.", "")
            url_domain = url_domain.replace(".", "_")
            url_domain = url_domain.replace("-", "_")
            url_path_name = urlparse(url).path.replace("/", "_").replace("+", "_")
            # if the path ends with a file extension (in the last 5 characters), remove it
            if "." in url_path_name[-5:]:
                url_path_name = url_path_name.rsplit(".", 1)[0]
            url_title = f"{url_domain}_{url_path_name}"
            return url_title

        url_title = url_title.replace(" ", "_").lower()
        url_title = "".join([c for c in url_title if c.isalnum() or c == "_"])
        return url_title

    async def _download_pdf_file(self, url: str) -> (str, str):
        try:
            response = requests.get(url)
            response.raise_for_status()
            pdf_filename = unquote(urlparse(url).path.split('/')[-1])

            if not pdf_filename:
                pdf_filename = f"{str(uuid.uuid4())}.pdf"

            # Save the PDF content to a file with the extracted name
            pdf_bytes = response.content

            presigned_url = await self._upload_bytes_to_s3_and_create_urls(
                file_bytes=pdf_bytes,
                output_filename=pdf_filename,
            )
            url_content = f"The PDF file has been saved to `{pdf_filename}` and can be downloaded from {presigned_url}"
            return url_content, pdf_filename
        except Exception as e:
            logging.error(f"Error downloading PDF file from {url}: {e}", extra={
                "session_id": self.agent_session.id,
            })
            raise e

    def _is_pdf_url(self, url: str) -> bool:
        # This regular expression pattern checks for a string ending with '.pdf'
        pattern = re.compile(r'\.pdf$', re.IGNORECASE)

        # Use the search method to look for the pattern at the end of the URL string
        return bool(pattern.search(url))

    def _is_image_url(self, url: str) -> bool:
        # This regular expression pattern checks for a string ending with an image file extension
        pattern = re.compile(r'\.(jpg|jpeg|png|gif|bmp)$', re.IGNORECASE)

        # Use the search method to look for the pattern at the end of the URL string
        return bool(pattern.search(url)) or "image;s=" in url

    async def save_url_and_add_it_to_uploaded_files(self,
                                                    url: str) -> (str, str, str):
        is_pdf_url = self._is_pdf_url(url)

        if is_pdf_url:
            url_content, url_title = await self._download_pdf_file(url)
            return url_title, url_content

        if self._is_image_url(url):
            try:
                image_extension = url.split(".")[-1]
                if image_extension.lower() not in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
                    image_extension = "webp"

                image_filename = f"{str(uuid.uuid4())}.{image_extension}"
                try:
                    image_bytes = requests.get(url, timeout=20).content
                except requests.Timeout:
                    return None, f"Failed to download the image within 20 seconds from {url}."
                except requests.ConnectionError:
                    return None, f"Failed to download the image due to connection problems from {url}."

                short_url, _ = await self._upload_bytes_to_s3_and_create_urls(
                    file_bytes=image_bytes,
                    output_filename=image_filename,
                )
                url_content = f"The image has been saved to `{image_filename}` and can be downloaded from {short_url}"

                return image_filename, url_content
            except Exception as e:
                logging.error(f"Error downloading image from {url}: {e}", extra={
                    "session_id": self.agent_session.id,
                })
                return None, f"Failed to download the image from {url} because of an error: {e}"

        # For other urls, we use the url title as the filename and save the content of the url to a file
        url_content, url_title = self._get_url_text_and_title(url)
        if url_content:
            url_title = self._clean_url_title(url_title, url)
            url_filename = f"{url_title}.txt" if url_title else f"{url}.txt"
            await self._upload_output_text_to_s3_and_create_url(text_to_upload=url_content,
                                                                output_filename=url_filename)
            return url_filename, url_content
        else:
            logging.error(f"Error extracting text from {url}", extra={
                "session_id": self.agent_session.id,
            })
            return None, None

    def _get_url_text_and_title(self, url):
        url_content, url_title = "", ""
        try:
            responses = extract_text_from_urls(
                urls=[url]
            )
            if responses:
                url_content = responses[0].get("url_content").get("decoded_content")
                url_title = responses[0].get("url_content").get("title")

        except Exception as e:
            logging.error(f"Error extracting text from {url}: {e}", extra={
                "session_id": self.agent_session.id,
            })
        return url_content, url_title

    async def execute(self):
        tool_input = self.SaveUrlAsFile(**self.tool_args)
        url_to_save = tool_input.url_to_save
        tool_call_id = str(uuid.uuid4())
        tool_icon_waiting = "line-md:downloading-loop"
        tool_icon_success = "material-symbols:download-for-offline-outline-rounded"
        tool_icon_error = "line-md:download-off-outline"
        try:
            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Saving the content of {url_to_save}.", tool_icon_waiting):
                yield update

            url_filename, url_content = await self.save_url_and_add_it_to_uploaded_files(url=url_to_save)

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Saved the content of {url_to_save} to `{url_filename}`.")
            self.add_additional_system_message(
                content="The url have been saved successfully. Don't update the user about this.")

            async for update in self.stream_update(tool_call_id, "tool_progress",
                                                   f"Saved the content of the url to `{url_filename}`",
                                                   tool_icon_success):
                yield update
        except Exception as e:
            logging.error(f"Error saving the content of {url_to_save}: {str(e)}")

            self.add_openai_function_call(arguments=self.tool_args)
            self.add_openai_function_response(content=f"Error saving the content of {url_to_save}: {str(e)}")
            self.add_additional_system_message(
                content="Explain why the content could not be saved and provide guidance to the user.")

            async for update in self.stream_update(tool_call_id, "tool_error",
                                                   "Something went wrong while saving the content of the url.",
                                                   tool_icon_error):
                yield update
