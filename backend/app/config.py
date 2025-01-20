from functools import lru_cache
from typing import Optional
from enum import Enum
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "Project Echo"
    project_version: str = "1.0.0"

    # Database configurations
    database_url: str = ""

    # Other configurations
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None
    s3_bucket_name: Optional[str] = "main_bucket"
    openai_audio_model: Optional[str] = "gpt-4o-audio-preview-2024-12-17"
    openai_image_model: Optional[str] = "dall-e-2"
    kokoro_base_url: Optional[str] = None

    # fastapi configurations
    stage: str = "local"

    # predefined fallback OpenAI models
    fallback_openai_models: list = [
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-turbo-preview",
    ]

    class Config:
        # This will read environment variables with the same name as the variables declared above from a .env file
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()


class ValidCharacterColour(str, Enum):
    LIGHT_BLUE = "#ADD8E6"
    LIGHT_GREEN = "#90EE90"
    LIGHT_YELLOW = "#FFFFE0"
    LIGHT_CORAL = "#F08080"
    LIGHT_PINK = "#FFB6C1"
    LIGHT_CYAN = "#E0FFFF"
    LIGHT_SALMON = "#FFA07A"
    LIGHT_GOLDENROD_YELLOW = "#FAFAD2"
    LAVENDER = "#E6E6FA"
    MISTY_ROSE = "#FFE4E1"


demo_configuration = {
  "demo_name": "voice_director_v1",
  "agent_configuration": {
    "create_character": {
      "is_enabled": True,
      "system_prompt_guidelines": f"### Create Character:\n- Creates a new character to be used in generating audio content.\n- Create engaging characters, even if they have negative attributes.\n- Share only the voice attributes, not the voice ID.\n- Only choose a valid colour from the following list: {', '.join([colour.value for colour in ValidCharacterColour])}"
    },
    "set_title": {
      "is_enabled": True,
      "system_prompt_guidelines": "### Set title\n- Set a suitable and engaging title and optional subtitle based on the audio content that will be generated.\n- Use set title in the following circumstances:\n    - User asks you to change the title or subtitle\n    - User asks you to generate a new audio content (e.g. a podcast, play, etc.) so choose the title base on the user's request.  "
    },
    "create_audio_segment": {
      "is_enabled": False,
      "system_prompt_guidelines": "### Create audio segment\n- Converts a transcript for a given character into audio using the character's assigned voice.\n- You can use this tool to generate engaging content and play with it to mimic realistic interruptions between characters.\n- In debates and most interactive audio content, characters should address eachother and have heated and emotional conversations to generate engaging content for the user.\n- The minimum number of audio segments to create is 25 audio segments unless requested otherwise by the user.\n- Use sounds effects like clapping, cars sounds, city, etc. when it provides value to the story.\n- Use music when approriate for intros, in-between scenes and in the end. You can also use it when required within the story.\n- There is a default character called \"Melody\" that will be added automatically which generates the music and sound effects so don't recreate it.\n- \"Melody\" sound effects and music `segment_text` examples to get inspired from and create similar but different ones when required:\n  - A deep, dramatic braam sound, perfect for creating tension and impact in a trailer\n  - Vintage radio, frequency change, interference, radio static\n  - A scary and weird sound from space, drums are getting louder and louder\n  - Ethereal, shimmering atmosphere for a mysterious scene\n  - Dogs barking\n  - Interface opening with a smooth whoosh\n  - Sound of large fire burning intensely, roaring flames creating a constant crackling and whooshing noise.\n  - Sirens in the distance, city sounds\n  - Horses galloping by\n  - Best emotional piano solo\n  - A lion roaring\n  - Footsteps on concrete\n  - Machine Gun\n  - Gunshots in an indoor shooting range with reverberation and echo.\n  - Short atmosphere magic start level in casual game\n  - Bubbling and boiling sound from a large cauldron in a medieval dungeon\n  - Choir of angels\n  - Tribal drums starting slow and building to a frenetic climax\n  - The rapid, staccato roll of a snare drum, with a crisp, precise rhythm\n  - A dramatic, dissonant, orchestral riser with swelling strings and brass\n  - Enchanting melody from a magical harp\n  - Pizzicato string quartet for a playful, bouncy effect\n  - Saxophone solo in A minor\n- Use create segment tool in the following circumstances:\n    - User asks you to add a specfic segment\n    - User asks you to generate a new audio content (e.g. a podcast, play, etc.) so call this tool as much as you need to generate the required and agreed content with the user. "
    },
    "save_url_as_file": {
      "is_enabled": False,
      "system_prompt_guidelines": "### Save URL as a file\n- Saves the content of a url as a file so it can be used to help answering the user's request.\n- Use the save url as a file tool in the following circumstances:\n    - User includes a url in their request "
    },
    "file_handling": {
      "is_enabled": True,
      "system_prompt_guidelines": "### File Handling Tool\n- Handles different types of operations (summarization, printing file content and Q&A) on files containing long text (e.g. pdf, docx, plain text, markdown and images)\n- When the task is question answering, break the user's request into smaller parts and search for each part separately (e.g. what is X and Y -> what is X, what is Y in two separate searches)\n- When the task is question answering, Retrieve more relevant information from the search results by asking more questions about the topic as it performs a vector search on the text to find the most relevant answer using each question as a query\n- When the task is summarisation, always provide a user_summary_request. If not specified by the user, always default to a detailed summary with a exact number of paragraphs to output of the number of main points to extract.\n- If the document summary is not suffecient to answer the user's request, utilise the summary to ask relavant questions to extract the required information from the document using Q&A mode.\n- Use file handling tool in the following circumstances:\n    - User asks you to summarize a long text (e.g. summarize this article, summarize this pdf, summarize this docx, summarize this image, etc.)\n    - User asks you to print the content of a long text (e.g. print this article, print this pdf, print this docx, print this image, etc.)\n    - User asks you to answer one or more questions about a long text (e.g. answer questions about this article, answer questions about this pdf, etc.)\n    - User asks you to extract text from an image or pdf (e.g. extract text from this image, extract text from this pdf, etc.)\n    - You are handling a more complex request that requires one or more of the above operations on a long text (e.g. summarize this article and answer questions about it, etc.)"
    },
    "generate_scene_dialogue": {
      "is_enabled": True,
      "system_prompt_guidelines": "### Generate scene dialogue\n- Generates dialogue for an entire scene or act based on the given characters and context.\n- Use this tool to create engaging and natural-sounding dialogue for a complete scene.\n- Provide a brief description of the scene, including setting and context.\n- List all characters participating in the scene.\n- Include any relevant knowledge extracted from documents to be used in the scene.\n- Specify the approximate duration of the scene in minutes.\n- The tool will internally generate dialogue that sounds human and avoids AI-like patterns.\n- The generated dialogue will include natural pauses, interruptions, and realistic conversation flow.\n- Use this tool when the user requests to create a new scene or act for their audio content.\n- The tool automatically maintains consistency with previously generated dialogue by referencing existing content.\n- Parallel Scene generation is not supported in order to maintain content coherence."
    },
    "create_sound_effect": {
      "is_enabled": False,
      "system_prompt_guidelines": "### Create sound effect\n- Creates a sound effect or music segment for the audio content.\n- Use this tool to add background music, ambient sounds, or specific sound effects to enhance the audio experience.\n- Provide a detailed description of the desired sound effect or music.\n- Specify the duration of the sound effect or music in seconds (maximum 30 seconds).\n- Use this tool when the user requests to add a specific sound effect or background music to a scene.\n- Suggest appropriate sound effects or music based on the scene context and mood."
    },
    "create_audio_outline": {
      "is_enabled": True,
      "system_prompt_guidelines": "### Create audio content outline\n- Creates the content outline for the different scenes to be generated.\n- Include detailed content description and knowledge based on the conversation so far to create accurate detailed outline that can create high quality coherent audio content."
    }
  }
}
