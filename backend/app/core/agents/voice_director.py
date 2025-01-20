from app.core.agents.agent import Agent
from app.services.prompt_reader import PromptReader
from app.core.tool_executor.tools import (
    CreateCharacterTool,
    SetTitleTool,
    CreateAudioSegmentTool,
    SaveUrlAsFileTool,
    FileHandlingTool,
    GenerateSceneDialogueTool,
    CreateSoundEffectTool,
    CreateAudioOutlineTool,
)
class VoiceDirector(Agent):
    workflow = "voice-director"
    prompt = PromptReader.get_prompt("assistants/voice_director.openai")
    models = ["gpt-4o-2024-11-20"]

    tools = [
        CreateCharacterTool,
        SetTitleTool,
        CreateAudioSegmentTool,
        SaveUrlAsFileTool,
        FileHandlingTool,
        GenerateSceneDialogueTool,
        CreateSoundEffectTool,
        CreateAudioOutlineTool,
    ]
