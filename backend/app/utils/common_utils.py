import logging
import re
from typing import List

import tiktoken
from PIL import Image
from langchain_text_splitters import RecursiveCharacterTextSplitter, TokenTextSplitter

from app.config import get_settings
logger = logging.getLogger(__name__)


async def perform_online_qa(
        questions: List[str],
        text_docs: List[str],
) -> str:
    """
    Performs online QA in parallel using the latest llama_index improvements.
    Embeddings calculations are optimized to happen in parallel batches.
    :param questions: the questions to ask
    :param text_docs: the text documents
    :return: the aggregated answer text
    """
    import asyncio
    import logging
    from typing import Tuple
    from llama_index.core import GPTVectorStoreIndex, Document
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.core.storage.storage_context import StorageContext
    from llama_index.core.vector_stores import SimpleVectorStore
    from llama_index.core import Settings
    
    logger = logging.getLogger(__name__)

    # Initialize the LLM and set up the service context with batch_size for embeddings
    model_name = "gpt-4o-mini"
    llm = OpenAI(
        model=model_name,
        temperature=0.5,
        api_key=get_settings().openai_api_key,
    )
    embed_model = OpenAIEmbedding(
        api_key=get_settings().openai_api_key,
        embed_batch_size=1000
    )
    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.context_window = 64000

    # Parse documents and create nodes
    parser = SimpleNodeParser()
    documents = [Document(text=text) for text in text_docs]
    nodes = parser.get_nodes_from_documents(documents)
    logger.info(f"Parsed {len(nodes)} nodes from documents.")

    # Build the index with optimized embeddings calculations
    vector_store = SimpleVectorStore()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = GPTVectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True
    )

    # Define an async function to handle concurrent question querying
    async def query_engine(question: str) -> Tuple[str, str]:
        try:
            query_engine = index.as_query_engine(similarity_top_k=10)
            generated_answer = await query_engine.aquery(question)
            logger.info(f"Question: {question}, Answer: {generated_answer}")
            return question, str(generated_answer)
        except Exception as exc:
            logger.error(f"Exception occurred while querying: {exc}")
            return question, f"Error: {exc}"

    # Schedule the execution of each question query asynchronously
    tasks = [query_engine(question) for question in questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    question_answer_pairs = {question: answer for question, answer in results}

    # Order the answers according to the original question ordering
    ordered_answers = [f"\n*{question}*\n\n{question_answer_pairs[question]}" for question in questions]

    # Combine answers into a single string to return
    answer_text = "\n".join(ordered_answers).strip()

    return answer_text


def resplit_long_text(input_items: List[str], chnk_size: int = 4000) -> List[str]:
    """
    Re-split a list of text items into chunks of a specified size, ensuring that each chunk does not exceed the
    specified size in terms of encoded length.

    :param input_items: A list of text items to be re-split.
    :param chnk_size: The maximum encoded length of each chunk. Default is 2000.
    :return: A list of text chunks, each with an encoded length not exceeding the specified chnk_size.
    """
    enc = tiktoken.encoding_for_model("gpt-4o")
    text_chunks = []
    text = ""

    for item in input_items:
        encoded_length = len(enc.encode(text + '\n' + item))

        if encoded_length > chnk_size:
            if text:
                text_chunks.append(text)
            text = item
        else:
            text += '\n' + item

    if text:
        text_chunks.append(text)

    logging.info(f"Long text re-split from {len(input_items)} into {len(text_chunks)} chunks")
    return text_chunks


def split_long_text(long_text: str,
                    chnk_size: int = 2000,
                    overlap: int = 200,
                    use_token_splitter: bool = True,
                    model="gpt-4o") -> List[str]:
    """
    Split the long text into chunks
    :param long_text: the long text
    :param chnk_size: number of tokens in a chunk
    :param overlap: overlap between chunks
    :param use_token_splitter: whether to use the token splitter
    :param model: the model name
    :return: the list of chunks
    """

    if use_token_splitter:
        text_splitter = TokenTextSplitter(
            model_name=model,
            chunk_size=chnk_size,
            chunk_overlap=overlap,
        )
        text_chunks = text_splitter.split_text(long_text)
    else:
        text_splitter = RecursiveCharacterTextSplitter().from_tiktoken_encoder(
            model_name=model,
            chunk_size=chnk_size,
            chunk_overlap=overlap,
        )
        text_chunks = text_splitter.split_text(long_text)
        text_chunks = resplit_long_text(text_chunks, chnk_size=chnk_size)

    logging.info(f"Long text split into {len(text_chunks)} chunks")
    return text_chunks



def resize_image(image: Image.Image,
                 convert="RGBA",
                 snap_size=8,
                 max_width_height: int = 1024,
                 limit_resize_to_max: bool = False) -> Image.Image:
    """
    This function is used to resize an image based on the constraints of the model.
    :param image: the image to resize
    :param convert: the color mode to convert the image to
    :param snap_size: the size to snap the image to
    :param max_width_height: the maximum width and height of the image
    :param limit_resize_to_max: whether to limit the resize to the max width and height
    :return: the resized image
    """
    image = image.convert(convert)
    w, h = image.size

    # Calculate the aspect ratio of the input image
    aspect_ratio = w / h

    # Determine the minimum and maximum dimensions for the resized image
    min_width, min_height = 512, 512
    max_width, max_height = max_width_height, max_width_height

    # Calculate the target width and height based on the aspect ratio and the constraints
    if aspect_ratio > 1:  # Landscape
        target_width = max(min_width, min(w, max_width))
        target_height = int(target_width / aspect_ratio)
        if target_height < min_height:
            target_height = min_height
            target_width = int(target_height * aspect_ratio)
    else:  # Portrait
        target_height = max(min_height, min(h, max_height))
        target_width = int(target_height * aspect_ratio)
        if target_width < min_width:
            target_width = min_width
            target_height = int(target_width / aspect_ratio)

    # Ensure the target width and height are multiples of 8
    target_width = (target_width // snap_size) * snap_size
    target_height = (target_height // snap_size) * snap_size

    # If the target width and height are the same as the max width and height, set them to 768
    if image.width == image.height and image.width >= min_width:
        target_width = 768
        target_height = 768

    if target_width == min_width and target_height == min_width and limit_resize_to_max:
        target_width = max_width_height
        target_height = max_width_height

    if target_width == 768 and target_height == 768 and limit_resize_to_max:
        target_width = max_width_height
        target_height = max_width_height

    # Increase the min quality of the image to 768x768 if it is 512x512
    if target_width == 512 and target_height == 512:
        target_width = 768
        target_height = 768

    # Resize the image
    logger.info(f"Resizing image from {image.size} to {target_width}x{target_height}")
    image = image.resize((target_width, target_height), resample=Image.LANCZOS)
    return image


def extract_file_name(file_path: str):
    """
    Extract file name from file path
    :param file_path: str
    :return: str
    """
    match = re.search(r'[^/]+$', file_path)
    if match:
        return match.group(0)
    return None